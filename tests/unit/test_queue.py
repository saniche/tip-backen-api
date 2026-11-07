import pytest
from fastapi import HTTPException
from redis.exceptions import ConnectionError

from shared.models import ProcessingJob, ProcessingJobType, ProcessingOutbox, User
from shared.queue import job_timeout, max_attempts, persist_work, publish_work


class FakeQueue:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    async def enqueue_job(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.fail:
            raise ConnectionError("unavailable")


@pytest.mark.asyncio
async def test_publish_uses_persisted_processing_job_id(database_session):
    user = User(email="queue@example.com", hashed_password="unused")
    database_session.add(user)
    database_session.flush()
    job = ProcessingJob(user_id=user.id, job_type=ProcessingJobType.MATCHING)
    outbox = persist_work(database_session, job, "matching", {"report_id": "report"})
    queue = FakeQueue()

    await publish_work(queue, database_session, outbox)

    assert queue.calls == [(("execute_processing_job", job.id), {"_job_id": job.id, "_queue_name": "arq:queue"})]
    assert database_session.get(ProcessingOutbox, job.id).last_dispatched_at is not None


@pytest.mark.asyncio
async def test_failed_enqueue_preserves_outbox_for_reconciliation(database_session):
    user = User(email="queue-failure@example.com", hashed_password="unused")
    database_session.add(user)
    database_session.flush()
    job = ProcessingJob(user_id=user.id, job_type=ProcessingJobType.MATCHING)
    outbox = persist_work(database_session, job, "matching", {"report_id": "report"})

    with pytest.raises(HTTPException) as error:
        await publish_work(FakeQueue(fail=True), database_session, outbox)

    assert error.value.status_code == 503
    database_session.expire_all()
    assert database_session.get(ProcessingOutbox, job.id).last_dispatched_at is None


@pytest.mark.parametrize("value", ["0", "4", "-1", "invalid"])
def test_retry_limit_is_bounded(monkeypatch, value):
    monkeypatch.setenv("ARQ_MAX_ATTEMPTS", value)
    with pytest.raises(ValueError, match="between 1 and 3"):
        max_attempts()


@pytest.mark.parametrize("value", ["0", "-1", "invalid"])
def test_job_timeout_must_be_positive(monkeypatch, value):
    monkeypatch.setenv("ARQ_JOB_TIMEOUT_SECONDS", value)
    with pytest.raises(ValueError, match="positive integer"):
        job_timeout()
