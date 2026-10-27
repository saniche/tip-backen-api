import matching.matching_service as matching_service
from shared.llm_structured import StructuredProviderError
from shared.models import Job, User, UserProfile


def test_matching_processing_persists_ranked_results_and_safe_owner_scope(client):
    user = client.post(
        "/api/v1/auth/register", json={"email": "match-int@example.com", "password": "password123"}
    ).json()
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.put("/api/v1/profile", headers=headers, json={"data": {"skills": ["Python"]}})
    first = client.post(
        "/api/v1/jobs/normalize",
        headers=headers,
        json={"url": "https://jobs.test/match-a", "content": "Python", "title": "Python"},
    )
    second = client.post(
        "/api/v1/jobs/normalize",
        headers=headers,
        json={"url": "https://jobs.test/match-b", "content": "SQL", "title": "SQL"},
    )
    response = client.post(
        "/api/v1/matching", headers=headers, json={"job_ids": [first.json()["id"], second.json()["id"]]}
    )

    assert response.status_code == 202
    detail = client.get(f"/api/v1/matching/reports/{response.json()['result_id']}", headers=headers).json()
    ranks = [item["rank"] for item in detail["results"]]
    assert ranks == sorted(ranks)
    assert all("explanation" in item for item in detail["results"])


def test_matching_invalid_structured_output_returns_safe_failure(client, monkeypatch):
    user = client.post(
        "/api/v1/auth/register", json={"email": "match-invalid@example.com", "password": "password123"}
    ).json()
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.put("/api/v1/profile", headers=headers, json={"data": {"skills": ["Python"]}})
    job = client.post(
        "/api/v1/jobs/normalize", headers=headers,
        json={"url": "https://jobs.test/match-invalid", "content": "Python", "title": "Python Engineer"},
    ).json()

    async def invalid_match(*args, **kwargs):
        raise StructuredProviderError("invalid structured output")

    monkeypatch.setattr(matching_service, "get_llm_match_output", invalid_match)
    response = client.post("/api/v1/matching", headers=headers, json={"job_ids": [job["id"]]})

    assert response.status_code == 202
    processing_job = client.get(f"/api/v1/processing-jobs/{response.json()['id']}", headers=headers)
    assert processing_job.json()["status"] == "failed"
    assert client.get("/api/v1/matching/reports", headers=headers).json()[0]["status"] == "failed"


def test_matching_api_serializes_empty_criteria_with_null_score(client, database_session):
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "match-empty@example.com", "password": "password123"},
    ).json()
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    user = database_session.query(User).filter_by(email="match-empty@example.com").one()
    database_session.add(
        UserProfile(user_id=user.id, data={"skills": ["Python"]}, output_language="English")
    )
    jobs = [
        Job(title="Python", required=["Python"], desirable=[], submitter_id=user.id),
        Job(title="Rust", required=["Rust"], desirable=[], submitter_id=user.id),
        Job(
            title="No criteria",
            required=[],
            desirable=[],
            tools_and_technologies=["Python"],
            key_responsibilities=["Build APIs"],
            submitter_id=user.id,
        ),
    ]
    database_session.add_all(jobs)
    database_session.commit()

    queued = client.post("/api/v1/matching", headers=headers, json={"job_ids": [job.id for job in jobs]})
    assert queued.status_code == 202
    report = client.get(
        f"/api/v1/matching/reports/{queued.json()['result_id']}",
        headers=headers,
    )

    assert report.status_code == 200
    results = report.json()["results"]
    assert [result["score"] for result in results] == [100, 0, None]
    assert [result["rank"] for result in results] == [1, 2, 3]
    assert results[-1]["scoring_status"] == "unscorable"
    assert results[-1]["explanation"]["requirements"] == []
    assert results[-1]["explanation"]["desirables"] == []
