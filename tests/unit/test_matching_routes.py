def test_matching_report_routes_exist_and_scope_by_owner(client):
    token = client.post(
        "/api/v1/auth/register", json={"email": "matcher@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post("/api/v1/profile/sessions", headers=headers)
    assert profile.status_code == 201

    user_profile = client.get("/api/v1/profile", headers=headers)
    assert user_profile.status_code == 404

    first = client.post(
        "/api/v1/jobs/normalize",
        headers=headers,
        json={
            "url": "https://jobs.test/alpha",
            "content": "Python Engineer with FastAPI",
            "company": "Acme",
            "title": "Python Engineer",
        },
    )
    second = client.post(
        "/api/v1/jobs/normalize",
        headers=headers,
        json={
            "url": "https://jobs.test/beta",
            "content": "Data Engineer with SQL",
            "company": "Acme",
            "title": "Data Engineer",
        },
    )
    assert first.status_code == 202
    assert second.status_code == 202

    profile_row = {
        "summary": "Python engineer with backend and API experience",
        "skills": ["Python", "FastAPI", "SQL"],
        "job_preferences": {"roles": ["Python Engineer"]},
    }
    client.put("/api/v1/profile", headers=headers, json={"data": profile_row})

    response = client.post(
        "/api/v1/matching", headers=headers, json={"job_ids": [first.json()["id"], second.json()["id"]]}
    )
    assert response.status_code == 202
    report_id = response.json()["report_id"]

    listed = client.get("/api/v1/matching/reports", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == report_id for item in listed.json())

    detail = client.get(f"/api/v1/matching/reports/{report_id}", headers=headers)
    assert detail.status_code == 200
    assert len(detail.json()["results"]) >= 1

    deleted = client.delete(f"/api/v1/matching/reports/{report_id}", headers=headers)
    assert deleted.status_code == 204
