import pytest
from fastapi import HTTPException
from redis.exceptions import ConnectionError
from sqlalchemy import func, select

import shared.queue as background_queue
from shared.models import CVRequest, Job, MatchReport, ProcessingJob, ProcessingOutbox, UserFile


@pytest.mark.parametrize("route", ["normalize", "profile", "matching", "match", "cv", "tailoring"])
def test_unavailable_redis_rejects_submission_without_committing(client, database_session, monkeypatch, route):
    registration = client.post(
        "/api/v1/auth/register", json={"email": "queue-user@example.com", "password": "password123"}
    ).json()
    headers = {"Authorization": f"Bearer {registration['access_token']}"}
    client.put("/api/v1/profile", headers=headers, json={"data": {"summary": "Python", "skills": ["Python"]}})
    job = client.post(
        "/api/v1/jobs/normalize",
        headers=headers,
        json={"url": "https://jobs.test/queue-setup", "content": "Python"},
    ).json()["id"]
    report = client.post("/api/v1/matching", headers=headers, json={"job_ids": [job]}).json()["result_id"]
    matching = client.get(f"/api/v1/matching/reports/{report}", headers=headers).json()["results"][0]["id"]
    session = client.post("/api/v1/profile/sessions", headers=headers, json={}).json()["id"]
    models = [ProcessingJob, ProcessingOutbox, Job, MatchReport, UserFile, CVRequest]
    before = [database_session.scalar(select(func.count()).select_from(model)) for model in models]

    async def unavailable():
        raise HTTPException(503, "Background processing is unavailable")

    monkeypatch.setattr(background_queue, "connect_queue", unavailable)
    if route == "normalize":
        response = client.post(
            "/api/v1/jobs/normalize", headers=headers,
            json={"url": "https://jobs.test/queue-unavailable", "content": "Python"},
        )
    elif route == "profile":
        response = client.post(
            f"/api/v1/profile/sessions/{session}/files", headers=headers,
            files={"file": ("profile.txt", b"Python", "text/plain")},
        )
    elif route == "matching":
        response = client.post("/api/v1/matching", headers=headers, json={"job_ids": [job]})
    elif route == "match":
        response = client.post("/api/v1/matching/match", headers=headers, json={"job_id": job})
    elif route == "cv":
        response = client.post("/api/v1/cv/tailor", headers=headers, json={"matching_ids": [matching]})
    else:
        response = client.post("/api/v1/tailoring", headers=headers, json={"job_ids": [job]})

    assert response.status_code == 503
    database_session.expire_all()
    assert [database_session.scalar(select(func.count()).select_from(model)) for model in models] == before
    assert database_session.scalar(select(Job).where(Job.url == "https://jobs.test/queue-unavailable")) is None


def test_ambiguous_enqueue_returns_503_and_retains_committed_work(client, database_session, monkeypatch):
    registration = client.post(
        "/api/v1/auth/register", json={"email": "queue-timeout@example.com", "password": "password123"}
    ).json()
    headers = {"Authorization": f"Bearer {registration['access_token']}"}

    class FailedQueue:
        async def enqueue_job(self, *args, **kwargs):
            raise ConnectionError("enqueue timed out")

        async def aclose(self):
            pass

    async def connect():
        return FailedQueue()

    monkeypatch.setattr(background_queue, "connect_queue", connect)
    response = client.post(
        "/api/v1/jobs/normalize", headers=headers,
        json={"url": "https://jobs.test/ambiguous", "content": "Python"},
    )

    assert response.status_code == 503
    job = database_session.scalar(select(Job).where(Job.url == "https://jobs.test/ambiguous"))
    assert job is not None and job.status == "pending"
    outbox = database_session.scalar(select(ProcessingOutbox).where(ProcessingOutbox.task_name == "job_normalize"))
    assert outbox is not None and outbox.arguments["job_id"] == job.id and outbox.last_dispatched_at is None
