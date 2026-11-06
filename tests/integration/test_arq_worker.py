import asyncio
import os
import subprocess
import sys
import time
import uuid

import pytest
from arq import create_pool
from arq.connections import RedisSettings
from arq.jobs import Job as ArqJob
from arq.jobs import JobStatus
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from shared.database import Base
from shared.models import (
    CVRequest,
    Job,
    JobInterest,
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    ProcessingOutbox,
    TailoredCVRecord,
    User,
    UserProfile,
)
from shared.queue import deserialize_job, serialize_job
from shared.storage import download_markdown


def _wait_for(check, process, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            return
        if process.poll() is not None:
            output, _ = process.communicate()
            pytest.fail(f"Worker exited unexpectedly: {output}")
        time.sleep(0.1)
    process.kill()
    output, _ = process.communicate(timeout=10)
    pytest.fail(f"Timed out waiting for the worker: {output}")


def _start_worker(environment, slow=False, tailoring=False, crash_after_upload=False):
    if tailoring:
        script = """
import os
import logging
logging.basicConfig(level=logging.INFO)
import tailoring.tailoring_router as router
from tailoring.tailoring_service import GeneratedDocument
async def fake_document(*args):
    return GeneratedDocument(content="# Shared document", filename="FILENAME")
router.generate_document = fake_document
CRASH_SETUP
from arq import run_worker
from shared.worker import WorkerSettings
run_worker(WorkerSettings)
"""
        script = script.replace("FILENAME", "first.md" if crash_after_upload else "cv.md")
        crash_setup = """
original_upload = router.upload_markdown
def crash_upload(*args):
    original_upload(*args)
    os._exit(42)
router.upload_markdown = crash_upload
""" if crash_after_upload else ""
        script = script.replace("CRASH_SETUP", crash_setup)
    else:
        script = """
import asyncio
import logging
logging.basicConfig(level=logging.INFO)
import jobs.job_normalizer as normalizer
async def fake_normalize(url, content):
    SLEEP
    return {"title": "Redis worker result"}
normalizer.normalize_job_content = fake_normalize
from arq import run_worker
from shared.worker import WorkerSettings
run_worker(WorkerSettings)
""".replace("SLEEP", "await asyncio.sleep(30)" if slow else "await asyncio.sleep(0)")
    return subprocess.Popen(
        [sys.executable, "-c", script],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _stop_worker(process):
    if process.poll() is None:
        process.kill()
    process.communicate(timeout=10)


@pytest.mark.parametrize("backend", ["sqlite", "postgres"])
@pytest.mark.parametrize("interrupt", [False, True])
def test_real_redis_worker_recovers_committed_work(tmp_path, interrupt, backend):
    redis_url = os.environ.get("TEST_REDIS_URL")
    if not redis_url:
        pytest.skip("Set TEST_REDIS_URL to an isolated Redis database")
    admin_engine = None
    schema = None
    if backend == "postgres":
        postgres_url = os.environ.get("TEST_POSTGRES_URL")
        if not postgres_url:
            pytest.skip("Set TEST_POSTGRES_URL to a disposable PostgreSQL database")
        schema = f"test_worker_{uuid.uuid4().hex}"
        admin_engine = create_engine(postgres_url)
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        separator = "&" if "?" in postgres_url else "?"
        database_url = f"{postgres_url}{separator}options=-csearch_path%3D{schema}"
    else:
        database_url = f"sqlite+pysqlite:///{tmp_path / 'worker.db'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email=f"{uuid.uuid4()}@example.com", hashed_password="unused")
        db.add(user)
        db.flush()
        job = Job(title="Pending", url=f"https://jobs.test/{uuid.uuid4()}", status="pending", submitter_id=user.id)
        processing = ProcessingJob(user_id=user.id, job_type=ProcessingJobType.JOB_NORMALIZE)
        db.add_all([job, processing])
        db.flush()
        processing_id, job_id = processing.id, job.id
        db.add(ProcessingOutbox(
            processing_job_id=processing_id,
            task_name="job_normalize",
            arguments={"job_id": job_id, "client_metadata": {}},
        ))
        db.commit()

    environment = os.environ.copy()
    environment.update({
        "DATABASE_URL": database_url,
        "REDIS_URL": redis_url,
        "ARQ_JOB_TIMEOUT_SECONDS": "3",
        "ARQ_MAX_ATTEMPTS": "3",
        "ARQ_QUEUE_NAME": f"tip:test:{uuid.uuid4()}",
        "JWT_SECRET_KEY": "integration-test-secret",
        "AZURE_STORAGE_CONNECTION_STRING": "UseDevelopmentStorage=true",
        "LOCAL_BLOB_DIRECTORY": str(tmp_path / "blobs"),
        "WORKER_LOCK_DIRECTORY": str(tmp_path / "locks"),
    })

    def job_state():
        with Session(engine) as db:
            return db.get(ProcessingJob, processing_id).status, db.get(ProcessingOutbox, processing_id).attempts

    process = _start_worker(environment, slow=interrupt)
    try:
        if interrupt:
            _wait_for(lambda: job_state()[1] == 1, process)
            _stop_worker(process)
            process = _start_worker(environment)
        _wait_for(lambda: job_state()[0] == ProcessingJobStatus.DONE, process)

        async def submit_duplicate():
            redis = await create_pool(
                RedisSettings.from_dsn(redis_url), default_queue_name=environment["ARQ_QUEUE_NAME"],
                job_serializer=serialize_job, job_deserializer=deserialize_job,
            )
            try:
                await redis.enqueue_job("execute_processing_job", processing_id, _job_id=processing_id)
                deadline = time.monotonic() + 10
                queued_job = ArqJob(processing_id, redis, _queue_name=environment["ARQ_QUEUE_NAME"])
                while time.monotonic() < deadline:
                    if await queued_job.status() == JobStatus.not_found:
                        return
                    await asyncio.sleep(0.1)
                raise AssertionError("Worker did not consume the duplicate")
            finally:
                await redis.aclose()

        asyncio.run(submit_duplicate())
        with Session(engine) as db:
            assert db.get(Job, job_id).title == "Redis worker result"
            assert db.get(ProcessingOutbox, processing_id).attempts == (2 if interrupt else 1)
            assert len(db.scalars(select(JobInterest).where(JobInterest.job_id == job_id)).all()) == 1
    finally:
        _stop_worker(process)
        engine.dispose()
        if admin_engine is not None:
            with admin_engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin_engine.dispose()


@pytest.mark.parametrize("interrupt", [False, True])
def test_real_worker_stores_documents_for_another_process(tmp_path, monkeypatch, interrupt):
    redis_url = os.environ.get("TEST_REDIS_URL")
    if not redis_url:
        pytest.skip("Set TEST_REDIS_URL to an isolated Redis database")
    database_url = f"sqlite+pysqlite:///{tmp_path / 'documents.db'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email=f"{uuid.uuid4()}@example.com", hashed_password="unused")
        db.add(user)
        db.flush()
        profile = UserProfile(user_id=user.id, data={"summary": "Python", "skills": []}, evidence={})
        job = Job(title="Example", status="completed", submitter_id=user.id)
        db.add_all([profile, job])
        db.flush()
        request = CVRequest(user_id=user.id, matching_ids=[], mode="general", status="processing",
                            job_ids=[job.id], profile_id=profile.id)
        processing = ProcessingJob(user_id=user.id, job_type=ProcessingJobType.CV_TAILOR)
        db.add_all([request, processing])
        db.flush()
        processing_id, request_id = processing.id, request.id
        db.add(ProcessingOutbox(
            processing_job_id=processing_id, task_name="tailoring", arguments={"request_id": request_id}
        ))
        db.commit()
    blobs = str(tmp_path / "blobs")
    environment = os.environ.copy()
    environment.update({
        "DATABASE_URL": database_url,
        "REDIS_URL": redis_url,
        "JWT_SECRET_KEY": "integration-test-secret",
        "AZURE_STORAGE_CONNECTION_STRING": "UseDevelopmentStorage=true",
        "LOCAL_BLOB_DIRECTORY": blobs,
        "WORKER_LOCK_DIRECTORY": str(tmp_path / "locks"),
        "ARQ_JOB_TIMEOUT_SECONDS": "3",
        "ARQ_QUEUE_NAME": f"tip:test:{uuid.uuid4()}",
    })

    def finished():
        with Session(engine) as db:
            return db.get(ProcessingJob, processing_id).status == ProcessingJobStatus.DONE

    process = _start_worker(environment, tailoring=True, crash_after_upload=interrupt)
    try:
        if interrupt:
            try:
                exit_code = process.wait(timeout=120)
            except subprocess.TimeoutExpired:
                process.kill()
                output, _ = process.communicate(timeout=10)
                pytest.fail(f"Worker did not reach the simulated crash: {output}")
            assert exit_code == 42
            process.communicate(timeout=10)
            process = _start_worker(environment, tailoring=True)
        _wait_for(finished, process)
        with Session(engine) as db:
            record = db.scalar(select(TailoredCVRecord).where(TailoredCVRecord.request_id == request_id))
            assert record is not None and record.status == "completed"
            path = record.blob_path
        monkeypatch.setenv("LOCAL_BLOB_DIRECTORY", blobs)
        assert download_markdown(path) == "# Shared document"
        assert path.endswith("first.md" if interrupt else "cv.md")
        assert len([item for item in (tmp_path / "blobs").rglob("*") if item.is_file()]) == 1
    finally:
        _stop_worker(process)
        engine.dispose()
