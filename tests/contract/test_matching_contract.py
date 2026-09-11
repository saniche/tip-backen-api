def test_matching_contract_ranks_results_and_denies_other_owner(client):
    first = client.post("/api/v1/auth/register", json={"email": "match-contract@example.com", "password": "password123"}).json()
    second = client.post("/api/v1/auth/register", json={"email": "match-other@example.com", "password": "password123"}).json()
    headers = {"Authorization": f"Bearer {first['access_token']}"}
    client.put("/api/v1/profile", headers=headers, json={"data": {"skills": ["Python", "FastAPI"]}})
    job = client.post(
        "/api/v1/jobs/normalize",
        headers=headers,
        json={"url": "https://jobs.test/matching-contract", "content": "Python FastAPI", "title": "Python Engineer"},
    )
    report = client.post("/api/v1/matching", headers=headers, json={"job_ids": [job.json()["id"]]})
    assert report.status_code == 202
    report_id = report.json()["report_id"]
    detail = client.get(f"/api/v1/matching/reports/{report_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["results"][0]["rank"] == 1
    assert "explanation" in detail.json()["results"][0]

    denied = client.get(
        f"/api/v1/matching/reports/{report_id}",
        headers={"Authorization": f"Bearer {second['access_token']}"},
    )
    assert denied.status_code == 404