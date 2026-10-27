import time

import jobs.job_normalizer as job_normalizer
from shared.llm_structured import StructuredProviderError


def test_job_normalization_deduplicates_and_exposes_structured_defaults(client):
    token = client.post(
        "/api/v1/auth/register", json={"email": "job-int@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "url": "https://jobs.test/integration",
        "content": "Python Engineer\nBuild APIs with FastAPI",
        "title": "Client Python Engineer",
        "company": "Client Acme",
        "location": "Client Remote",
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
    assert job["title"] == "Client Python Engineer"
    assert job["company"] == "Client Acme"
    assert job["location"] == "Client Remote"
    assert job["salary"] == "$100,000-$120,000 CAD"
    assert job["source"] == "Other"
    assert job["posting_date"] == "2026-10-15"
    assert job["requirements"] == ["Python"]
    assert job["desirables"] == ["FastAPI"]
    assert "Python" in job["tools_and_technologies"]
    assert "technical_stack" not in job
    assert job["additionals"] == ["Health benefits"]


def test_job_normalization_extracts_metadata_when_client_fields_are_absent(client):
    token = client.post(
        "/api/v1/auth/register", json={"email": "job-content-only@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": "Bearer " + token}
    created = client.post(
        "/api/v1/jobs/normalize",
        headers=headers,
        json={"url": "https://www.indeed.com/viewjob?jk=abc", "content": "Software Engineer posting"},
    )

    assert created.status_code == 202
    job = client.get(f"/api/v1/jobs/{created.json()['id']}", headers=headers).json()
    assert job["title"] == "Normalized Software Engineer"
    assert job["company"] == "Normalized Employer"
    assert job["location"] == "Toronto, Ontario"
    assert job["source"] == "Indeed"
    assert job["requirements"] == ["Python"]


def test_job_normalization_requires_url_and_content(client):
    token = client.post(
        "/api/v1/auth/register", json={"email": "job-invalid-request@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": "Bearer " + token}

    assert client.post("/api/v1/jobs/normalize", headers=headers, json={"url": "https://jobs.test"}).status_code == 422


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
