import time

import pytest

import cv.cv_tailoring as cv_tailoring
import cv.cv_tailoring_router as cv_tailoring_router
from shared.llm_structured import StructuredProviderError


@pytest.mark.parametrize("valid", [True, False])
def test_cv_experience_validates_profile_fields_and_reports_failure_to_owner(client, monkeypatch, valid):
    token = client.post(
        "/api/v1/auth/register", json={"email": "cv-experience@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.put(
        "/api/v1/profile",
        headers=headers,
        json={"data": {
            "summary": "Nurse", "skills": [],
            "WorkExperiences": [{
                "Title": "Nurse", "Company": "Care Hospital", "StartDate": "2020", "EndDate": "2023",
                "RealisationDescription": ["Delivered patient care"],
            }],
        }},
    )
    job = client.post(
        "/api/v1/jobs/normalize", headers=headers,
        json={"url": "https://jobs.test/cv-experience", "content": "Python", "title": "Python Engineer"},
    ).json()
    report = client.post("/api/v1/matching", headers=headers, json={"job_ids": [job["id"]]}).json()
    match_id = client.get(f"/api/v1/matching/reports/{report['result_id']}", headers=headers).json()["results"][0]["id"]
    calls = []

    async def provider(system, user, schema_model, **kwargs):
        calls.append(user)
        return schema_model(
            target_role="Python Engineer", summary="Nurse", skills=[], education=[], certifications=[],
            experience=[{
                "profile_index": 0, "title": "Community Care Lead",
                "company": "Care Hospital" if valid else "Wrong Hospital",
                "start_date": "2020", "end_date": "2023",
                "summary": "Supported patient care.",
                "descriptions": ["Delivered patient care"],
                "description_evidence": [["RealisationDescription='Delivered patient care'"]],
            }],
            education_evidence=[], certification_evidence=[],
        )

    monkeypatch.setattr(cv_tailoring, "call_openai_structured", provider)
    request = client.post("/api/v1/cv/tailor", headers=headers, json={"matching_id": match_id}).json()
    status = client.get(f"/api/v1/processing-jobs/{request['id']}", headers=headers).json()
    if valid:
        assert status["status"] == "done"
        assert len(calls) == 1
        text = client.get(f"/api/v1/cv/{status['result_id']}/download", headers=headers).text
        assert "Community Care Lead | Care Hospital | 2020 - 2023" in text
        assert "Supported patient care." in text
        assert "Delivered patient care" in text
    else:
        assert status["status"] == "failed"
        assert len(calls) == 2
        assert "company" in status["error"] and "Wrong Hospital" in status["error"]
        assert "Care Hospital" in status["error"]
        assert client.get("/api/v1/cv", headers=headers).json() == []
        other_token = client.post(
            "/api/v1/auth/register", json={"email": "cv-other@example.com", "password": "password123"}
        ).json()["access_token"]
        assert client.get(
            f"/api/v1/processing-jobs/{request['id']}", headers={"Authorization": f"Bearer {other_token}"}
        ).status_code == 404


def test_cv_skills_do_not_trigger_grounding_retries(client, monkeypatch):
    token = client.post(
        "/api/v1/auth/register", json={"email": "cv-grounding@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.put(
        "/api/v1/profile",
        headers=headers,
        json={"data": {"summary": "Python engineer", "skills": ["Python"], "soft_skills": ["Communication"]}},
    )
    job = client.post(
        "/api/v1/jobs/normalize",
        headers=headers,
        json={"url": "https://jobs.test/cv-grounding", "content": "Python", "title": "Python Engineer"},
    ).json()
    report = client.post("/api/v1/matching", headers=headers, json={"job_ids": [job["id"]]}).json()
    match_id = client.get(f"/api/v1/matching/reports/{report['result_id']}", headers=headers).json()["results"][0]["id"]
    calls = []

    async def provider(system, user, schema_model, **kwargs):
        calls.append(user)
        return schema_model(
            target_role="Python Engineer",
            summary="Award-winning Rust architect",
            experience=[],
            education=[],
            certifications=[],
            skills=["FastAPI", "Patient assessment"],
            education_evidence=[],
            certification_evidence=[],
        )

    monkeypatch.setattr(cv_tailoring, "call_openai_structured", provider)
    request = client.post("/api/v1/cv/tailor", headers=headers, json={"matching_id": match_id}).json()
    status = client.get(f"/api/v1/processing-jobs/{request['id']}", headers=headers).json()

    assert len(calls) == 1
    assert status["status"] == "done"
    cvs = client.get("/api/v1/cv", headers=headers).json()
    assert len(cvs) == 1
    text = client.get(f"/api/v1/cv/{status['result_id']}/download", headers=headers).text
    assert "Award-winning Rust architect" in text
    assert "FastAPI" in text
    assert "Patient assessment" in text


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
    match_id = client.get(f"/api/v1/matching/reports/{report['result_id']}", headers=headers).json()["results"][0]["id"]
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
    match_id = client.get(f"/api/v1/matching/reports/{report['result_id']}", headers=headers).json()["results"][0]["id"]

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
    match_id = client.get(f"/api/v1/matching/reports/{report['result_id']}", headers=headers).json()["results"][0]["id"]

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
    match_id = client.get(f"/api/v1/matching/reports/{report['result_id']}", headers=headers).json()["results"][0]["id"]

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
    matching_ids = [item["id"] for item in client.get(f"/api/v1/matching/reports/{report['result_id']}", headers=headers).json()["results"]]
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
