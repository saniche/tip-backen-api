import matching.matching_service as matching_service
from shared.llm_structured import StructuredProviderError
from tests.keycloak_stub import issue_token


def test_matching_contract_ranks_results_and_denies_other_owner(client):
    first = issue_token(client, "match-contract@example.com")
    second = issue_token(client, "match-other@example.com")
    headers = {"Authorization": f"Bearer {first['access_token']}"}
    client.post("/api/v1/profile", headers=headers, json={"data": {"skills": ["Python", "FastAPI"]}})
    job = client.post(
        "/api/v1/jobs/normalize",
        headers=headers,
        json={"url": "https://jobs.test/matching-contract", "content": "Python FastAPI", "title": "Python Engineer"},
    )
    report = client.post("/api/v1/matching", headers=headers, json={"job_ids": [job.json()["id"]]})
    assert report.status_code == 202
    report_id = report.json()["result_id"]
    detail = client.get(f"/api/v1/matching/reports/{report_id}", headers=headers)
    assert detail.status_code == 200
    listed = client.get("/api/v1/matching/reports", headers=headers)
    assert detail.json()["profile_id"] == listed.json()[0]["profile_id"]
    assert detail.json()["results"][0]["rank"] == 1
    assert "explanation" in detail.json()["results"][0]
    assert set(detail.json()["results"][0]["explanation"]) == {
        "requirements",
        "desirables",
        "notes",
        "analysis",
    }

    denied = client.get(
        f"/api/v1/matching/reports/{report_id}",
        headers={"Authorization": f"Bearer {second['access_token']}"},
    )
    assert denied.status_code == 404


def test_matching_contract_returns_safe_provider_failure(client, monkeypatch):
    token = issue_token(client, "match-provider-failure@example.com")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/profile", headers=headers, json={"data": {"skills": ["Python"]}})
    job = client.post(
        "/api/v1/jobs/normalize",
        headers=headers,
        json={"url": "https://jobs.test/provider-failure", "content": "Python", "title": "Python Engineer"},
    ).json()

    async def fail_matching(*args, **kwargs):
        raise StructuredProviderError("External processing failed.")

    monkeypatch.setattr(matching_service, "get_llm_match_output", fail_matching)
    response = client.post("/api/v1/matching", headers=headers, json={"job_ids": [job["id"]]})

    assert response.status_code == 202
    processing_job = client.get(f"/api/v1/processing-jobs/{response.json()['id']}", headers=headers)
    assert processing_job.json()["status"] == "failed"
    assert processing_job.json()["error"] == "Matching failed"
