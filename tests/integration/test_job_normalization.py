def test_job_normalization_deduplicates_and_exposes_structured_defaults(client):
    token = client.post("/api/v1/auth/register", json={"email": "job-int@example.com", "password": "password123"}).json()["access_token"]
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

    assert first.status_code == 201
    assert second.json()["status"] == "existing"
    job = client.get(f"/api/v1/jobs/{first.json()['id']}", headers=headers).json()
    assert job["title"] == "Python Engineer"
    assert job["company"] == "Acme"
    assert "Python" in job["technical_stack"]