import hashlib
import logging
import os
from contextlib import contextmanager
from pathlib import Path

from arq import Retry, cron
from arq.jobs import Job as ArqJob
from arq.jobs import JobStatus as ArqJobStatus
from filelock import FileLock
from filelock import Timeout as FileLockTimeout
from sqlalchemy import select, text
from sqlalchemy.orm import Session

import shared.config  # noqa: F401
from shared.database import SessionLocal, engine
from shared.models import (
    CVRequest,
    Job,
    MatchReport,
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingOutbox,
    ProfileFileStatus,
    ProfileSession,
    ProfileSessionStatus,
    UserFile,
)
from shared.processing_artifacts import artifact_id
from shared.queue import (
    deserialize_job,
    job_timeout,
    max_attempts,
    publish_work,
    queue_name,
    redis_settings,
    serialize_job,
)
from shared.retry import is_transient_failure
from shared.storage import build_blob_path, delete_blob

logger = logging.getLogger("tip-api")


@contextmanager
def execution_lock(identity: str):
    digest = hashlib.sha256(identity.encode("utf-8")).digest()
    if engine.dialect.name == "postgresql":
        key = int.from_bytes(digest[:8], "big", signed=True)
        with engine.connect() as connection:
            acquired = connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key}).scalar_one()
            connection.commit()
            try:
                yield acquired, connection if acquired else None
            finally:
                if acquired:
                    connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
                    connection.commit()
    elif engine.dialect.name == "sqlite":
        directory = Path(os.environ.get("WORKER_LOCK_DIRECTORY", ".worker-locks"))
        directory.mkdir(parents=True, exist_ok=True)
        lock = FileLock(str(directory / f"{digest.hex()}.lock"), timeout=0)
        try:
            lock.acquire()
        except FileLockTimeout:
            yield False, None
        else:
            try:
                yield True, None
            finally:
                lock.release()
    else:
        raise RuntimeError(f"Unsupported worker database: {engine.dialect.name}")


def _lock_identity(outbox: ProcessingOutbox) -> str:
    if outbox.task_name == "profile":
        return f"profile:{outbox.arguments['session_id']}"
    return f"processing-job:{outbox.processing_job_id}"


def _open_session(connection) -> Session:
    return Session(bind=connection, expire_on_commit=False) if connection is not None else SessionLocal()


def _fail_exhausted(db: Session, job: ProcessingJob, outbox: ProcessingOutbox) -> None:
    arguments = outbox.arguments
    filenames = arguments.get("artifact_filenames", [])
    for index, filename in enumerate(filenames):
        if filename:
            delete_blob(build_blob_path(job.user_id, artifact_id(job.id, index), filename))

    messages = {
        "profile": "Profile processing failed",
        "job_normalize": "Job normalization failed",
        "matching": "Matching failed",
        "cv_tailoring": "CV generation failed",
        "tailoring": "Tailoring failed",
    }
    message = messages.get(outbox.task_name, "Background processing failed")
    if outbox.task_name == "profile":
        session = db.get(ProfileSession, arguments["session_id"])
        if session is not None:
            session.status = ProfileSessionStatus.FAILED
        for file in db.execute(select(UserFile).where(UserFile.session_id == arguments["session_id"])).scalars():
            if file.status != ProfileFileStatus.COMPLETED:
                file.status = ProfileFileStatus.FAILED
                file.error = message
    elif outbox.task_name == "job_normalize":
        normalized_job = db.get(Job, arguments["job_id"])
        if normalized_job is not None:
            normalized_job.status = "failed"
    elif outbox.task_name == "matching":
        report = db.get(MatchReport, arguments["report_id"])
        if report is not None:
            report.status = "failed"
    elif outbox.task_name in {"cv_tailoring", "tailoring"}:
        request = db.get(CVRequest, arguments["request_id"])
        if request is not None:
            request.status, request.error = "failed", message
    job.status, job.error = ProcessingJobStatus.FAILED, message
    db.commit()
    logger.error("Background job failed after its final attempt", extra={"processing_job_id": job.id})


async def _run_handler(name: str, job_id: str, args: dict, db: Session, retry_transient: bool) -> None:
    if name == "profile":
        from profile.profile_builder_router import _run_profile_session

        await _run_profile_session(args["session_id"], args["user_id"], job_id, db=db, retry_transient=retry_transient)
    elif name == "job_normalize":
        from jobs.job_normalizer import _run_job_normalization

        await _run_job_normalization(
            job_id, args["job_id"], args["client_metadata"], db=db, retry_transient=retry_transient
        )
    elif name == "matching":
        from matching.job_matching_router import _run_match_report

        await _run_match_report(
            job_id, args["report_id"], args["user_id"], args["job_ids"], db=db, retry_transient=retry_transient
        )
    elif name == "cv_tailoring":
        from cv.cv_tailoring_router import _run_cv_tailoring

        await _run_cv_tailoring(
            job_id, args["user_id"], args["matching_ids"], args["mode"], args["output_language"],
            args["request_id"], db=db, retry_transient=retry_transient,
        )
    elif name == "tailoring":
        from tailoring.tailoring_router import _run_tailoring

        await _run_tailoring(job_id, args["request_id"], db=db, retry_transient=retry_transient)
    else:
        raise ValueError(f"Unknown background task: {name}")


async def execute_processing_job(ctx: dict, job_id: str) -> None:
    with SessionLocal() as db:
        outbox = db.get(ProcessingOutbox, job_id)
        if outbox is None:
            raise ValueError("Background job outbox entry not found")
        identity = _lock_identity(outbox)
    with execution_lock(identity) as (acquired, connection):
        if not acquired:
            raise Retry(defer=10)
        db = _open_session(connection)
        try:
            outbox = db.get(ProcessingOutbox, job_id)
            job = db.get(ProcessingJob, job_id)
            if outbox is None or job is None:
                raise ValueError("Background job not found")
            if job.status in {ProcessingJobStatus.DONE, ProcessingJobStatus.FAILED}:
                return
            limit = max_attempts()
            if outbox.attempts >= limit:
                _fail_exhausted(db, job, outbox)
                return
            outbox.attempts += 1
            attempt = outbox.attempts
            args, name = dict(outbox.arguments), outbox.task_name
            db.commit()
            try:
                await _run_handler(name, job_id, args, db, attempt < limit)
            except Exception as exc:
                logger.exception("Background job attempt failed", extra={"processing_job_id": job_id})
                if attempt < limit and is_transient_failure(exc):
                    raise Retry(defer=min(60, 2 ** attempt)) from exc
                with _open_session(connection) as failure_db:
                    failure_job = failure_db.get(ProcessingJob, job_id)
                    failure_outbox = failure_db.get(ProcessingOutbox, job_id)
                    if failure_job is None or failure_outbox is None:
                        raise
                    _fail_exhausted(failure_db, failure_job, failure_outbox)
                raise
        finally:
            db.close()


async def reconcile_processing_jobs(ctx: dict) -> None:
    with SessionLocal() as db:
        rows = db.execute(
            select(ProcessingOutbox)
            .join(ProcessingJob, ProcessingJob.id == ProcessingOutbox.processing_job_id)
            .where(ProcessingJob.status.in_([ProcessingJobStatus.PENDING, ProcessingJobStatus.RUNNING]))
        ).scalars().all()
        pending = [(row.processing_job_id, _lock_identity(row)) for row in rows]
    for job_id, identity in pending:
        with execution_lock(identity) as (acquired, connection):
            if not acquired:
                continue
            with _open_session(connection) as db:
                outbox, job = db.get(ProcessingOutbox, job_id), db.get(ProcessingJob, job_id)
                if outbox is None or job is None or job.status in {
                    ProcessingJobStatus.DONE, ProcessingJobStatus.FAILED
                }:
                    continue
                state = await ArqJob(job_id, ctx["redis"], _queue_name=queue_name()).status()
                if state != ArqJobStatus.not_found:
                    continue
                if outbox.attempts >= max_attempts():
                    _fail_exhausted(db, job, outbox)
                else:
                    await publish_work(ctx["redis"], db, outbox)


async def startup(ctx: dict) -> None:
    max_attempts()
    if engine.dialect.name == "sqlite" and engine.url.database in {None, "", ":memory:"}:
        raise RuntimeError("The worker requires a database shared with the API, not in-memory SQLite")
    with engine.connect() as connection:
        connection.execute(select(ProcessingOutbox.processing_job_id).limit(1))


class WorkerSettings:
    functions = [execute_processing_job]
    queue_name = queue_name()
    cron_jobs = [cron(
        reconcile_processing_jobs,
        name=f"reconcile_{hashlib.sha256(queue_name.encode()).hexdigest()[:16]}",
        second={0, 30},
        run_at_startup=True,
    )]
    redis_settings = redis_settings()
    job_serializer = serialize_job
    job_deserializer = deserialize_job
    on_startup = startup
    # Lock-contention retries are not executions; the database enforces the actual attempt limit.
    max_tries = 1_000_000
    keep_result = 0
    health_check_interval = 30
    job_timeout = job_timeout()
