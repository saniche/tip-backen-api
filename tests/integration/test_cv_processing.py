import time

import cv_tailoring_router
from llm_structured import StructuredProviderError


def test_cv_processing_persists_markdown_and_expiring_download_url(client):
    token = client.post(
        "/api/v1/auth/register", json={"email": "cv-int@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.put("/api/v1/profile", headers=headers, json={"data": {"summary": "Python engineer", "skills": ["Python"]}})
    job = client.post(
        "/api/v1/jobs/normalize",
        headers=headers,
        json={"url": "https://jobs.test/cv-int", "content": "Python", "title": "Python Engineer"},
    )
    report = client.post("/api/v1/matching", headers=headers, json={"job_ids": [job.json()["id"]]}).json()
    match_id = client.get(f"/api/v1/matching/reports/{report['report_id']}", headers=headers).json()["results"][0]["id"]
    request = client.post("/api/v1/cv/tailor", headers=headers, json={"matching_id": match_id})
    for _ in range(20):
        status = client.get(f"/api/v1/processing-jobs/{request.json()['id']}", headers=headers)
        if status.json().get("result_id"):
            break
        time.sleep(0.01)
    response = client.get(f"/api/v1/cv/{status.json()['result_id']}/download", headers=headers)
    assert response.status_code == 200
    assert "Tailored CV" in response.text
    assert "sig=" in response.headers["x-temporary-download-url"]


def test_cv_provider_failure_publishes_no_record(client, monkeypatch):
    token = client.post(
        "/api/v1/auth/register", json={"email": "cv-failure@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.put("/api/v1/profile", headers=headers, json={"data": {"skills": ["Python"]}})
    job = client.post(
        "/api/v1/jobs/normalize", headers=headers,
        json={"url": "https://jobs.test/cv-failure", "content": "Python", "title": "Python Engineer"},
    ).json()
    report = client.post("/api/v1/matching", headers=headers, json={"job_ids": [job["id"]]}).json()
    match_id = client.get(f"/api/v1/matching/reports/{report['report_id']}", headers=headers).json()["results"][0]["id"]

    async def fail_cv(*args, **kwargs):
        raise StructuredProviderError("provider unavailable")

    monkeypatch.setattr(cv_tailoring_router, "build_tailored_cv", fail_cv)
    request = client.post("/api/v1/cv/tailor", headers=headers, json={"matching_id": match_id}).json()
    status = client.get(f"/api/v1/processing-jobs/{request['id']}", headers=headers).json()

    assert status["status"] == "failed"
    assert client.get("/api/v1/cv", headers=headers).json() == []


def test_cv_invalid_structured_output_publishes_no_record(client, monkeypatch):
    token = client.post(
        "/api/v1/auth/register", json={"email": "cv-invalid@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.put("/api/v1/profile", headers=headers, json={"data": {"skills": ["Python"]}})
    job = client.post(
        "/api/v1/jobs/normalize", headers=headers,
        json={"url": "https://jobs.test/cv-invalid", "content": "Python", "title": "Python Engineer"},
    ).json()
    report = client.post("/api/v1/matching", headers=headers, json={"job_ids": [job["id"]]}).json()
    match_id = client.get(f"/api/v1/matching/reports/{report['report_id']}", headers=headers).json()["results"][0]["id"]

    async def invalid_cv(*args, **kwargs):
        raise StructuredProviderError("invalid structured output")

    monkeypatch.setattr(cv_tailoring_router, "build_tailored_cv", invalid_cv)
    request = client.post("/api/v1/cv/tailor", headers=headers, json={"matching_id": match_id}).json()

    assert client.get(f"/api/v1/processing-jobs/{request['id']}", headers=headers).json()["status"] == "failed"
    assert client.get("/api/v1/cv", headers=headers).json() == []


def test_cv_upload_failure_rolls_back_flushed_record(client, monkeypatch):
    token = client.post(
        "/api/v1/auth/register", json={"email": "cv-upload-failure@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.put("/api/v1/profile", headers=headers, json={"data": {"skills": ["Python"]}})
    job = client.post(
        "/api/v1/jobs/normalize", headers=headers,
        json={"url": "https://jobs.test/cv-upload-failure", "content": "Python", "title": "Python Engineer"},
    ).json()
    report = client.post("/api/v1/matching", headers=headers, json={"job_ids": [job["id"]]}).json()
    match_id = client.get(f"/api/v1/matching/reports/{report['report_id']}", headers=headers).json()["results"][0]["id"]

    def fail_upload(*args, **kwargs):
        raise RuntimeError("storage unavailable")

    monkeypatch.setattr(cv_tailoring_router, "upload_markdown", fail_upload)
    request = client.post("/api/v1/cv/tailor", headers=headers, json={"matching_id": match_id}).json()
    status = client.get(f"/api/v1/processing-jobs/{request['id']}", headers=headers).json()

    assert status["status"] == "failed"
    assert client.get("/api/v1/cv", headers=headers).json() == []


def test_later_multi_cv_failure_deletes_earlier_uploaded_blob(client, monkeypatch):
    token = client.post(
        "/api/v1/auth/register", json={"email": "cv-multi-failure@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.put("/api/v1/profile", headers=headers, json={"data": {"skills": ["Python"]}})
    job_ids = []
    for suffix in ("one", "two"):
        job_ids.append(client.post(
            "/api/v1/jobs/normalize", headers=headers,
            json={"url": f"https://jobs.test/cv-multi-{suffix}", "content": "Python", "title": "Python Engineer"},
        ).json()["id"])
    report = client.post("/api/v1/matching", headers=headers, json={"job_ids": job_ids}).json()
    matching_ids = [item["id"] for item in client.get(f"/api/v1/matching/reports/{report['report_id']}", headers=headers).json()["results"]]
    uploaded = []
    deleted = []

    def upload_then_fail(path, content):
        uploaded.append(path)
        if len(uploaded) == 2:
            raise RuntimeError("second upload failed")

    monkeypatch.setattr(cv_tailoring_router, "upload_markdown", upload_then_fail)
    monkeypatch.setattr(cv_tailoring_router, "delete_blob", deleted.append)
    request = client.post("/api/v1/cv/tailor", headers=headers, json={"matching_ids": matching_ids, "mode": "per_job"}).json()
    status = client.get(f"/api/v1/processing-jobs/{request['id']}", headers=headers).json()

    assert status["status"] == "failed"
    assert deleted == [uploaded[0]]
    assert client.get("/api/v1/cv", headers=headers).json() == []
