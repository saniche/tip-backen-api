from shared.models import JobInterest


def test_job_deduplication_filters_and_interest(client):
    token = client.post("/api/v1/auth/register", json={"email": "jobs@example.com", "password": "password123"}).json()[
        "access_token"
    ]
    headers = {"Authorization": f"Bearer {token}"}
    first = client.post(
        "/api/v1/jobs/normalize",
        headers=headers,
        json={"url": "https://jobs.test/1", "content": "Python Engineer", "company": "Acme"},
    )
    assert first.status_code == 202
    processing = client.get(f"/api/v1/processing-jobs/{first.json()['processing_job_id']}", headers=headers)
    assert processing.status_code == 200
    second = client.post(
        "/api/v1/jobs/normalize",
        headers=headers,
        json={"url": "https://jobs.test/1", "content": "Python Engineer", "company": "Acme"},
    )
    assert second.json()["status"] == "existing"
    job_id = first.json()["id"]
    assert len(client.get("/api/v1/jobs?company=Acme", headers=headers).json()) == 1
    # Normalization already created the submitter's interest, so the manual add finds it.
    assert client.post(f"/api/v1/jobs/{job_id}/interest", headers=headers).status_code == 201
    assert client.post(f"/api/v1/jobs/{job_id}/interest", headers=headers).json()["status"] == "existing"
    listed = client.get("/api/v1/jobs/interests", headers=headers).json()
    assert [item["jobId"] for item in listed["items"]] == [job_id]


def test_job_contract_supports_pagination_date_filter_and_delete_authorization(client):
    first = client.post(
        "/api/v1/auth/register", json={"email": "submitter@example.com", "password": "password123"}
    ).json()
    second = client.post("/api/v1/auth/register", json={"email": "other@example.com", "password": "password123"}).json()
    headers = {"Authorization": f"Bearer {first['access_token']}"}
    job = client.post(
        "/api/v1/jobs/normalize",
        headers=headers,
        json={"url": "https://jobs.test/contract", "content": "Data Engineer", "company": "Acme"},
    )
    assert job.status_code == 202
    listed = client.get("/api/v1/jobs?page=1&limit=1&saved_after=2000-01-01", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    denied = client.delete(
        f"/api/v1/jobs/{job.json()['id']}", headers={"Authorization": f"Bearer {second['access_token']}"}
    )
    assert denied.status_code == 403


def test_deleting_a_job_removes_interests_held_in_it(client, database_session):
    submitter = client.post(
        "/api/v1/auth/register", json={"email": "del-submitter@example.com", "password": "password123"}
    ).json()["access_token"]
    follower = client.post(
        "/api/v1/auth/register", json={"email": "del-follower@example.com", "password": "password123"}
    ).json()["access_token"]
    submitter_headers = {"Authorization": "Bearer " + submitter}
    follower_headers = {"Authorization": "Bearer " + follower}
    job_id = client.post(
        "/api/v1/jobs/normalize",
        headers=submitter_headers,
        json={"url": "https://jobs.test/delete-interest", "content": "Data Engineer", "company": "Acme"},
    ).json()["id"]
    assert client.post(f"/api/v1/jobs/{job_id}/interest", headers=follower_headers).status_code == 201

    deleted = client.delete(f"/api/v1/jobs/{job_id}", headers=submitter_headers)

    assert deleted.status_code == 204
    assert database_session.query(JobInterest).count() == 0
    assert client.get("/api/v1/jobs/interests", headers=follower_headers).json()["total"] == 0
