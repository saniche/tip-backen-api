import time


def test_cv_tailoring_and_download_flow(client):
    token = client.post("/api/v1/auth/register", json={"email": "cv@example.com", "password": "password123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.put("/api/v1/profile", headers=headers, json={"data": {"summary": "Python engineer", "skills": ["Python", "FastAPI"]}})
    assert profile.status_code == 200

    job = client.post("/api/v1/jobs/normalize", headers=headers, json={"url": "https://jobs.test/cv", "content": "Python Engineer with FastAPI and SQL", "company": "Acme", "title": "Python Engineer"})
    assert job.status_code == 202

    match_response = client.post("/api/v1/matching", headers=headers, json={"job_ids": [job.json()["id"]]})
    assert match_response.status_code == 202
    report_id = match_response.json()["report_id"]

    report = client.get(f"/api/v1/matching/reports/{report_id}", headers=headers)
    assert report.status_code == 200
    match_id = report.json()["results"][0]["id"]

    cv_job = client.post("/api/v1/cv/tailor", headers=headers, json={"matching_id": match_id, "output_language": "English"})
    assert cv_job.status_code == 202
    processing_job_id = cv_job.json()["id"]

    proc = None
    for _ in range(20):
        proc = client.get(f"/api/v1/processing-jobs/{processing_job_id}", headers=headers)
        if proc.json().get("result_id") is not None:
            break
        time.sleep(0.05)

    assert proc is not None and proc.status_code == 200
    assert proc.json().get("result_id") is not None

    cv_response = client.get(f"/api/v1/cv/{proc.json()['result_id']}/download", headers=headers)
    assert cv_response.status_code == 200
    assert "text/markdown" in cv_response.headers.get("content-type", "")
