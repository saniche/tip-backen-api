def test_matching_processing_persists_ranked_results_and_safe_owner_scope(client):
    user = client.post("/api/v1/auth/register", json={"email": "match-int@example.com", "password": "password123"}).json()
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.put("/api/v1/profile", headers=headers, json={"data": {"skills": ["Python"]}})
    first = client.post("/api/v1/jobs/normalize", headers=headers, json={"url": "https://jobs.test/match-a", "content": "Python", "title": "Python"},)
    second = client.post("/api/v1/jobs/normalize", headers=headers, json={"url": "https://jobs.test/match-b", "content": "SQL", "title": "SQL"},)
    response = client.post("/api/v1/matching", headers=headers, json={"job_ids": [first.json()["id"], second.json()["id"]]})

    assert response.status_code == 202
    detail = client.get(f"/api/v1/matching/reports/{response.json()['report_id']}", headers=headers).json()
    ranks = [item["rank"] for item in detail["results"]]
    assert ranks == sorted(ranks)
    assert all("explanation" in item for item in detail["results"])