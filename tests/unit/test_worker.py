import asyncio

import pytest
from arq import Retry
from arq.jobs import JobStatus

import shared.worker as worker
from shared.database import TestingSessionLocal, testing_engine
from shared.models import Job, ProcessingJob, ProcessingJobStatus, ProcessingJobType, ProcessingOutbox, User


@pytest.fixture
def worker_database(monkeypatch, tmp_path):
    monkeypatch.setattr(worker, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(worker, "engine", testing_engine)
    monkeypatch.setenv("WORKER_LOCK_DIRECTORY", str(tmp_path))


def _create_job(db):
    user = User(email="worker@example.com", hashed_password="unused")
    db.add(user)
    db.flush()
    job = Job(title="Example", url="https://jobs.test/worker", status="pending", submitter_id=user.id)
    processing = ProcessingJob(user_id=user.id, job_type=ProcessingJobType.JOB_NORMALIZE)
    db.add_all([job, processing])
    db.flush()
    db.add(ProcessingOutbox(
        processing_job_id=processing.id,
        task_name="job_normalize",
        arguments={"job_id": job.id, "client_metadata": {}},
    ))
    db.commit()
    return processing.id, job.id


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [1, 2, 3])
async def test_attempts_are_bounded_and_exhaustion_is_visible(worker_database, database_session, monkeypatch, limit):
    job_id, normalized_id = _create_job(database_session)
    monkeypatch.setenv("ARQ_MAX_ATTEMPTS", str(limit))
    attempts = []

    async def fail(name, processing_id, args, db, retry_transient):
        attempts.append(retry_transient)
        db.close()
        raise TimeoutError("provider unavailable")

    monkeypatch.setattr(worker, "_run_handler", fail)
    for _ in range(limit - 1):
        with pytest.raises(Retry):
            await worker.execute_processing_job({}, job_id)
    with pytest.raises(TimeoutError):
        await worker.execute_processing_job({}, job_id)
    await worker.execute_processing_job({}, job_id)

    database_session.expire_all()
    assert attempts == [True] * (limit - 1) + [False]
    assert database_session.get(ProcessingOutbox, job_id).attempts == limit
    assert database_session.get(ProcessingJob, job_id).status == ProcessingJobStatus.FAILED
    assert database_session.get(Job, normalized_id).status == "failed"


@pytest.mark.asyncio
async def test_concurrent_duplicate_waits_and_completed_job_is_not_replayed(
    worker_database, database_session, monkeypatch
):
    job_id, _ = _create_job(database_session)
    started, release = asyncio.Event(), asyncio.Event()
    calls = []

    async def complete(name, processing_id, args, db, retry_transient):
        calls.append(processing_id)
        started.set()
        await release.wait()
        db.get(ProcessingJob, processing_id).status = ProcessingJobStatus.DONE
        db.commit()
        db.close()

    monkeypatch.setattr(worker, "_run_handler", complete)
    running = asyncio.create_task(worker.execute_processing_job({}, job_id))
    await started.wait()
    with pytest.raises(Retry):
        await worker.execute_processing_job({}, job_id)
    release.set()
    await running
    await worker.execute_processing_job({}, job_id)
    assert calls == [job_id]


@pytest.mark.asyncio
async def test_reconciler_republishes_lost_work_and_fails_exhausted_work(
    worker_database, database_session, monkeypatch
):
    job_id, normalized_id = _create_job(database_session)

    class MissingJob:
        def __init__(self, job_id, redis, _queue_name):
            pass

        async def status(self):
            return JobStatus.not_found

    class Queue:
        def __init__(self):
            self.calls = []

        async def enqueue_job(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    monkeypatch.setattr(worker, "ArqJob", MissingJob)
    queue = Queue()
    await worker.reconcile_processing_jobs({"redis": queue})
    assert queue.calls == [(("execute_processing_job", job_id), {"_job_id": job_id, "_queue_name": "arq:queue"})]

    database_session.expire_all()
    database_session.get(ProcessingOutbox, job_id).attempts = 3
    database_session.get(ProcessingJob, job_id).status = ProcessingJobStatus.RUNNING
    database_session.commit()
    await worker.reconcile_processing_jobs({"redis": queue})
    database_session.expire_all()
    assert database_session.get(ProcessingJob, job_id).status == ProcessingJobStatus.FAILED
    assert database_session.get(Job, normalized_id).status == "failed"
