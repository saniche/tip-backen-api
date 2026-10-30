import time

import cv.cv_tailoring_router as cv_tailoring_router
from cv.cv_tailoring import GroundingError
from shared import storage

API = "/api/v1"


def _matches(client, email, count=1):
    token = client.post(f"{API}/auth/register", json={"email": email, "password": "password123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = client.put(
        f"{API}/profile", headers=headers, json={"data": {"summary": "Python engineer", "skills": ["Python"]}}
    ).json()["user_id"]
    jobs = [
        client.post(
            f"{API}/jobs/normalize",
            headers=headers,
            json={"url": f"https://jobs.test/{email}/{i}", "content": "Python", "title": "Python Engineer"},
        ).json()["id"]
        for i in range(count)
    ]
    report = client.post(f"{API}/matching", headers=headers, json={"job_ids": jobs}).json()
    results = client.get(f"{API}/matching/reports/{report['result_id']}", headers=headers).json()["results"]
    return headers, user_id, [item["id"] for item in results]


def _blobs(user_id):
    return [key for key in storage._LOCAL_BLOB_STORE if key.startswith(user_id)]


def test_deleting_a_tailored_cv_also_deletes_its_stored_file(client):
    headers, user_id, matchings = _matches(client, "legacy-delete@example.com")
    job = client.post(f"{API}/cv/tailor", headers=headers, json={"matching_id": matchings[0]}).json()
    for _ in range(20):
        result_id = client.get(f"{API}/processing-jobs/{job['id']}", headers=headers).json().get("result_id")
        if result_id:
            break
        time.sleep(0.01)
    assert len(_blobs(user_id)) == 1

    assert client.delete(f"{API}/cv/{result_id}", headers=headers).status_code == 204

    assert _blobs(user_id) == []
    assert client.get(f"{API}/cv", headers=headers).json() == []


def test_group_all_builds_one_cv_from_the_whole_group(client, monkeypatch):
    headers, user_id, matchings = _matches(client, "legacy-group@example.com", count=2)
    captured = []
    original = cv_tailoring_router.build_tailored_cv

    async def spy(profile, job_data, match_score, output_language="English", **kwargs):
        captured.append(job_data)
        return await original(profile, job_data, match_score, output_language, **kwargs)

    monkeypatch.setattr(cv_tailoring_router, "build_tailored_cv", spy)
    job = client.post(f"{API}/cv/tailor", headers=headers, json={"matching_ids": matchings, "mode": "group_all"}).json()

    assert client.get(f"{API}/processing-jobs/{job['id']}", headers=headers).json()["status"] == "done"
    assert len(captured) == 1 and captured[0].title == "Python Engineer"
    cvs = client.get(f"{API}/cv", headers=headers).json()
    assert len(cvs) == 1 and cvs[0]["target_job_ids"] and len(cvs[0]["target_job_ids"]) == 2
    assert all("/" not in key.split("/", 2)[-1] for key in _blobs(user_id))  # file name has no path separators


def test_validation_failures_are_reported_with_a_specific_message(client, monkeypatch):
    headers, user_id, matchings = _matches(client, "legacy-grounding@example.com")

    async def ungrounded(*args, **kwargs):
        raise GroundingError("Tailored CV contains unsupported experience content: Google")

    monkeypatch.setattr(cv_tailoring_router, "build_tailored_cv", ungrounded)
    job = client.post(f"{API}/cv/tailor", headers=headers, json={"matching_id": matchings[0]}).json()
    status = client.get(f"{API}/processing-jobs/{job['id']}", headers=headers).json()

    assert status["status"] == "failed"
    assert status["error"].startswith("CV validation failed")
    assert "unsupported experience content: Google" in status["error"]
