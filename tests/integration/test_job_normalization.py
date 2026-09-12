import time

import job_normalizer
from llm_structured import StructuredProviderError


def test_job_normalization_deduplicates_and_exposes_structured_defaults(client):
    token = client.post(
        "/api/v1/auth/register", json={"email": "job-int@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "url": "https://jobs.test/integration",
        "content": "Python Engineer\nBuild APIs with FastAPI",
        "title": "Python Engineer",
        "company": "Acme",
        "location": "Remote",
    }
    first = client.post("/api/v1/jobs/normalize", headers=headers, json=payload)
    second = client.post("/api/v1/jobs/normalize", headers=headers, json=payload)

    assert first.status_code == 202
    for _ in range(20):
        status = client.get(f"/api/v1/processing-jobs/{first.json()['processing_job_id']}", headers=headers)
        if status.json().get("result_id"):
            break
        time.sleep(0.01)
    assert status.json().get("result_id") == first.json()["id"]
    assert second.json()["status"] == "existing"
    job = client.get(f"/api/v1/jobs/{first.json()['id']}", headers=headers).json()
    assert job["title"] == "Python Engineer"
    assert job["company"] == "Acme"
    assert "Python" in job["technical_stack"]


def test_job_provider_failure_marks_job_and_processing_failed(client, monkeypatch):
    token = client.post(
        "/api/v1/auth/register", json={"email": "job-failure@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    async def fail_normalization(*args, **kwargs):
        raise StructuredProviderError("provider unavailable")

    monkeypatch.setattr(job_normalizer, "normalize_job_content", fail_normalization)
    created = client.post(
        "/api/v1/jobs/normalize", headers=headers,
        json={"url": "https://jobs.test/failure", "content": "Python", "title": "Python Engineer"},
    ).json()
    status = client.get(f"/api/v1/processing-jobs/{created['processing_job_id']}", headers=headers).json()
    job = client.get(f"/api/v1/jobs/{created['id']}", headers=headers).json()

    assert status["status"] == "failed"
    assert job["status"] == "failed"


def test_job_invalid_structured_output_is_not_matchable(client, monkeypatch):
    token = client.post(
        "/api/v1/auth/register", json={"email": "job-invalid@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    async def invalid_normalization(*args, **kwargs):
        raise StructuredProviderError("invalid structured output")

    monkeypatch.setattr(job_normalizer, "normalize_job_content", invalid_normalization)
    created = client.post(
        "/api/v1/jobs/normalize", headers=headers,
        json={"url": "https://jobs.test/invalid", "content": "Python", "title": "Python Engineer"},
    ).json()

    assert client.get(f"/api/v1/processing-jobs/{created['processing_job_id']}", headers=headers).json()["status"] == "failed"
    client.put("/api/v1/profile", headers=headers, json={"data": {"skills": ["Python"]}})
    assert client.post("/api/v1/matching", headers=headers, json={"job_ids": [created["id"]]}).status_code == 400
