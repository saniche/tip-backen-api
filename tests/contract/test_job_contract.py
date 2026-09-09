def test_job_deduplication_filters_and_interest(client):
    token = client.post("/api/v1/auth/register", json={"email": "jobs@example.com", "password": "password123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    first = client.post("/api/v1/jobs/normalize", headers=headers, json={"url": "https://jobs.test/1", "content": "Python Engineer", "company": "Acme"})
    assert first.status_code == 201
    second = client.post("/api/v1/jobs/normalize", headers=headers, json={"url": "https://jobs.test/1", "content": "Python Engineer", "company": "Acme"})
    assert second.json()["status"] == "existing"
    job_id = first.json()["id"]
    assert len(client.get("/api/v1/jobs?company=Acme", headers=headers).json()) == 1
    assert client.post(f"/api/v1/jobs/{job_id}/interest", headers=headers).status_code == 201
    assert client.post(f"/api/v1/jobs/{job_id}/interest", headers=headers).json()["status"] == "existing"
