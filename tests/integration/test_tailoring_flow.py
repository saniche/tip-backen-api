from datetime import datetime, timedelta, timezone

import cover_letter.cover_letter_tailoring as cover_letter_module
import cv.cv_tailoring as cv_module
import tailoring.tailoring_service as tailoring_service
from cover_letter.cover_letter_tailoring import CoverLetterGroundingError
from shared import storage
from shared.database import TestingSessionLocal
from shared.llm_structured import StructuredProviderError
from shared.models import UserProfile

API = "/api/v1"


def _setup(client, email, job_count=2):
    token = client.post(f"{API}/auth/register", json={"email": email, "password": "password123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = client.put(
        f"{API}/profile", headers=headers, json={"data": {"summary": "Python engineer", "skills": ["Python"]}}
    ).json()["user_id"]
    job_ids = []
    for index in range(job_count):
        job = client.post(
            f"{API}/jobs/normalize",
            headers=headers,
            json={"url": f"https://jobs.test/{email}/{index}", "content": "Python", "title": "Python Engineer"},
        )
        job_ids.append(job.json()["id"])
    return headers, user_id, job_ids


def _tailor(client, headers, **payload):
    return client.post(f"{API}/tailoring", headers=headers, json=payload)


def _detail(client, headers, response):
    return client.get(f"{API}/tailoring/requests/{response.json()['result_id']}", headers=headers).json()


def _blobs(user_id):
    return [key for key in storage._LOCAL_BLOB_STORE if key.startswith(user_id)]


def test_per_job_cv_and_general_cover_letter(client):
    headers, user_id, jobs = _setup(client, "flow@example.com")

    response = _tailor(
        client, headers, job_ids=jobs, cv_mode="per_job", cover_letter={"enabled": True, "mode": "general"}
    )

    assert response.status_code == 202
    assert client.get(f"{API}/processing-jobs/{response.json()['id']}", headers=headers).json()["status"] == "done"
    detail = _detail(client, headers, response)
    assert detail["status"] == "completed" and detail["cover_letter"] == {"enabled": True, "mode": "general"}
    cvs = [d for d in detail["documents"] if d["kind"] == "cv"]
    letters = [d for d in detail["documents"] if d["kind"] == "cover_letter"]
    assert sorted(d["job_id"] for d in cvs) == sorted(jobs) and all(d["scope"] == "per_job" for d in cvs)
    assert len(letters) == 1 and letters[0]["scope"] == "general" and letters[0]["job_id"] is None
    assert letters[0]["job_ids"] == jobs
    assert all(d["status"] == "completed" and d["download_url"] for d in detail["documents"])
    letter_text = client.get(f"{API}/tailoring/documents/{letters[0]['id']}/download", headers=headers).text
    assert "Dear Hiring Manager," in letter_text and "Hiring Team" in letter_text
    cv_text = client.get(f"{API}/tailoring/documents/{cvs[0]['id']}/download", headers=headers).text
    assert "## Python Engineer" in cv_text


def test_cover_letter_is_optional_and_general_cv_produces_one_document(client):
    headers, _, jobs = _setup(client, "cv-only@example.com")

    detail = _detail(client, headers, _tailor(client, headers, job_ids=jobs, cv_mode="general"))

    assert [(d["kind"], d["scope"]) for d in detail["documents"]] == [("cv", "general")]
    assert detail["documents"][0]["job_ids"] == jobs and detail["cover_letter"]["enabled"] is False


def test_selected_profile_is_used_and_latest_is_the_default(client):
    headers, user_id, jobs = _setup(client, "profiles@example.com", job_count=1)
    older = client.get(f"{API}/profiles", headers=headers).json()[0]["id"]
    with TestingSessionLocal() as db:
        newest = UserProfile(
            user_id=user_id,
            data={"summary": "Python engineer"},
            evidence={},
            output_language="English",
            created_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        db.add(newest)
        db.commit()
        newest_id = newest.id

    default = _detail(client, headers, _tailor(client, headers, job_ids=jobs))
    selected = _detail(client, headers, _tailor(client, headers, job_ids=jobs, profile_id=older))

    assert default["profile_id"] == newest_id
    assert selected["profile_id"] == older
    assert {d["id"] for d in default["documents"]} and all(d["status"] == "completed" for d in selected["documents"])


def test_default_documents_are_only_a_style_reference_and_are_optional(client, monkeypatch):
    headers, _, jobs = _setup(client, "style@example.com", job_count=1)
    seen = {}

    async def cv_provider(system, user, schema_model, **kwargs):
        seen["cv"] = user
        return schema_model(
            target_role="Python Engineer",
            summary="Python Engineer",
            experience=[],
            education=[],
            certifications=[],
            skills=["Python"],
            summary_evidence=["Python Engineer"],
            experience_evidence=[],
            education_evidence=[],
            certification_evidence=[],
        )

    async def letter_provider(system, user, schema_model, **kwargs):
        seen["letter"] = user
        return schema_model(greeting="Hello,", paragraphs=["I am a Python engineer."], closing="Regards,")

    monkeypatch.setattr(cv_module, "call_openai_structured", cv_provider)
    monkeypatch.setattr(cover_letter_module, "call_openai_structured", letter_provider)
    both = {"job_ids": jobs, "cover_letter": {"enabled": True, "mode": "per_job"}}

    _tailor(client, headers, **both)
    assert "style_reference" not in seen["cv"] and "style_reference" not in seen["letter"]
    assert "Python engineer" in seen["cv"] and "Python engineer" in seen["letter"]  # the profile is always sent

    client.put(f"{API}/defaults/cv", headers=headers, json={"content": "My usual CV voice"})
    client.put(f"{API}/defaults/cover-letter", headers=headers, json={"content": "My usual letter voice"})
    detail = _detail(client, headers, _tailor(client, headers, **both))

    assert "'style_reference': 'My usual CV voice'" in seen["cv"]
    assert "'style_reference': 'My usual letter voice'" in seen["letter"]
    assert "Python engineer" in seen["cv"] and "Python engineer" in seen["letter"]
    assert detail["status"] == "completed"


def test_invalid_requests_are_rejected(client):
    headers, user_id, jobs = _setup(client, "invalid@example.com", job_count=1)

    assert _tailor(client, headers, job_ids=jobs, cover_letter={"enabled": True}).status_code == 422
    assert _tailor(client, headers, job_ids=[]).status_code == 422
    assert _tailor(client, headers, job_ids=[f"j{i}" for i in range(11)]).status_code == 422
    assert _tailor(client, headers, job_ids=jobs, cv_mode="group_all").status_code == 422
    assert _tailor(client, headers, job_ids=["missing"]).status_code == 404
    assert _tailor(client, headers, job_ids=jobs, profile_id="missing").status_code == 404
    profile_id = client.get(f"{API}/profiles", headers=headers).json()[0]["id"]
    client.delete(f"{API}/profiles/{profile_id}", headers=headers)
    assert _tailor(client, headers, job_ids=jobs, profile_id=profile_id).status_code == 404
    assert _tailor(client, headers, job_ids=jobs).status_code == 404  # no active profile left


def test_duplicate_job_ids_are_collapsed(client):
    headers, _, jobs = _setup(client, "dupes@example.com", job_count=1)

    detail = _detail(client, headers, _tailor(client, headers, job_ids=[jobs[0], jobs[0]]))

    assert detail["job_ids"] == jobs and len(detail["documents"]) == 1


def test_one_failed_document_does_not_discard_the_others(client, monkeypatch):
    headers, user_id, jobs = _setup(client, "partial@example.com", job_count=1)

    async def broken_letter(*args, **kwargs):
        raise CoverLetterGroundingError("Cover letter contains unsupported facts: Google")

    monkeypatch.setattr(tailoring_service, "build_cover_letter", broken_letter)
    response = _tailor(client, headers, job_ids=jobs, cover_letter={"enabled": True, "mode": "per_job"})
    detail = _detail(client, headers, response)

    assert detail["status"] == "partial"
    by_kind = {d["kind"]: d for d in detail["documents"]}
    assert by_kind["cv"]["status"] == "completed" and by_kind["cv"]["download_url"]
    assert by_kind["cover_letter"]["status"] == "failed" and by_kind["cover_letter"]["download_url"] is None
    assert "not supported" in by_kind["cover_letter"]["error"]
    assert client.get(f"{API}/processing-jobs/{response.json()['id']}", headers=headers).json()["status"] == "done"
    assert (
        client.get(f"{API}/tailoring/documents/{by_kind['cover_letter']['id']}/download", headers=headers).status_code
        == 404
    )


def test_when_everything_fails_the_processing_job_fails_with_a_useful_error(client, monkeypatch):
    headers, user_id, jobs = _setup(client, "all-fail@example.com", job_count=1)

    async def down(*args, **kwargs):
        raise StructuredProviderError("provider unavailable")

    monkeypatch.setattr(tailoring_service, "build_tailored_cv", down)
    response = _tailor(client, headers, job_ids=jobs)
    status = client.get(f"{API}/processing-jobs/{response.json()['id']}", headers=headers).json()

    assert status["status"] == "failed" and "try again" in status["error"]
    assert _detail(client, headers, response)["status"] == "failed"
    assert client.get(f"{API}/cv", headers=headers).json() == []
    assert _blobs(user_id) == []


def test_deleting_a_request_or_document_removes_the_stored_files(client):
    headers, user_id, jobs = _setup(client, "cleanup@example.com")

    response = _tailor(client, headers, job_ids=jobs, cover_letter={"enabled": True, "mode": "general"})
    detail = _detail(client, headers, response)
    assert len(_blobs(user_id)) == 3

    assert (
        client.delete(f"{API}/tailoring/documents/{detail['documents'][0]['id']}", headers=headers).status_code == 204
    )
    assert len(_blobs(user_id)) == 2
    assert client.delete(f"{API}/tailoring/requests/{detail['id']}", headers=headers).status_code == 204
    assert _blobs(user_id) == []
    assert client.get(f"{API}/tailoring/requests/{detail['id']}", headers=headers).status_code == 404


def test_requests_and_documents_are_private_to_their_owner(client):
    headers, _, jobs = _setup(client, "owner-t@example.com", job_count=1)
    other, _, _ = _setup(client, "other-t@example.com", job_count=1)
    detail = _detail(client, headers, _tailor(client, headers, job_ids=jobs))
    document_id = detail["documents"][0]["id"]

    assert client.get(f"{API}/tailoring/requests/{detail['id']}", headers=other).status_code == 404
    assert client.delete(f"{API}/tailoring/requests/{detail['id']}", headers=other).status_code == 404
    assert client.get(f"{API}/tailoring/documents/{document_id}/download", headers=other).status_code == 404
    assert client.delete(f"{API}/tailoring/documents/{document_id}", headers=other).status_code == 404
    assert client.get(f"{API}/tailoring/requests", headers=other).json() == []
    assert [item["id"] for item in client.get(f"{API}/tailoring/requests", headers=headers).json()] == [detail["id"]]
