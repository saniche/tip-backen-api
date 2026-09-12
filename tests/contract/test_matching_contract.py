import matching_service
from llm_structured import StructuredProviderError


def test_matching_contract_ranks_results_and_denies_other_owner(client):
    first = client.post(
        "/api/v1/auth/register", json={"email": "match-contract@example.com", "password": "password123"}
    ).json()
    second = client.post(
        "/api/v1/auth/register", json={"email": "match-other@example.com", "password": "password123"}
    ).json()
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


def test_matching_contract_returns_safe_provider_failure(client, monkeypatch):
    token = client.post(
        "/api/v1/auth/register", json={"email": "match-provider-failure@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.put("/api/v1/profile", headers=headers, json={"data": {"skills": ["Python"]}})
    job = client.post(
        "/api/v1/jobs/normalize",
        headers=headers,
        json={"url": "https://jobs.test/provider-failure", "content": "Python", "title": "Python Engineer"},
    ).json()

    async def fail_matching(*args, **kwargs):
        raise StructuredProviderError("External processing failed.")

    monkeypatch.setattr(matching_service, "get_llm_match_output", fail_matching)
    response = client.post("/api/v1/matching", headers=headers, json={"job_ids": [job["id"]]})

    assert response.status_code == 502
    assert response.json()["error"] == {
        "code": "SERVICE_UNAVAILABLE",
        "message": "External processing failed. Please try again later.",
        "details": None,
        "request_id": None,
    }
