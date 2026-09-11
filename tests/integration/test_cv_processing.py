import time


def test_cv_processing_persists_markdown_and_expiring_download_url(client):
    token = client.post("/api/v1/auth/register", json={"email": "cv-int@example.com", "password": "password123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.put("/api/v1/profile", headers=headers, json={"data": {"summary": "Python engineer", "skills": ["Python"]}})
    job = client.post("/api/v1/jobs/normalize", headers=headers, json={"url": "https://jobs.test/cv-int", "content": "Python", "title": "Python Engineer"})
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