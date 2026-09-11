import time


def _profile_and_match(client, email, url):
    token = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.put("/api/v1/profile", headers=headers, json={"data": {"summary": "Python engineer", "skills": ["Python"]}})
    job = client.post("/api/v1/jobs/normalize", headers=headers, json={"url": url, "content": "Python", "title": "Python Engineer"})
    report = client.post("/api/v1/matching", headers=headers, json={"job_ids": [job.json()["id"]]}).json()
    detail = client.get(f"/api/v1/matching/reports/{report['report_id']}", headers=headers).json()
    return headers, detail["results"][0]["id"]


def test_cv_contract_supports_group_all_and_owner_scoped_crud(client):
    headers, matching_id = _profile_and_match(client, "cv-contract@example.com", "https://jobs.test/cv-contract")
    response = client.post("/api/v1/cv/tailor", headers=headers, json={"matching_ids": [matching_id], "mode": "group_all"})
    assert response.status_code == 202
    status = None
    for _ in range(20):
        status = client.get(f"/api/v1/processing-jobs/{response.json()['id']}", headers=headers)
        if status.json().get("result_id"):
            break
        time.sleep(0.01)
    cv_id = status.json()["result_id"]
    assert client.get("/api/v1/cv", headers=headers).status_code == 200
    assert client.get(f"/api/v1/cv/{cv_id}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/cv/{cv_id}/download", headers=headers).status_code == 200
    assert client.delete(f"/api/v1/cv/{cv_id}", headers=headers).status_code == 204


def test_cv_contract_denies_cross_owner_access(client):
    owner_headers, matching_id = _profile_and_match(client, "cv-owner@example.com", "https://jobs.test/cv-owner")
    other_token = client.post("/api/v1/auth/register", json={"email": "cv-other@example.com", "password": "password123"}).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}
    response = client.post("/api/v1/cv/tailor", headers=owner_headers, json={"matching_id": matching_id})
    for _ in range(20):
        status = client.get(f"/api/v1/processing-jobs/{response.json()['id']}", headers=owner_headers)
        if status.json().get("result_id"):
            break
        time.sleep(0.01)
    assert client.get(f"/api/v1/cv/{status.json()['result_id']}", headers=other_headers).status_code == 404