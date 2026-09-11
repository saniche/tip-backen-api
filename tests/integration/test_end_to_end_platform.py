import time


def test_profile_to_cv_acceptance_flow(client):
    token = client.post("/api/v1/auth/register", json={"email": "e2e@example.com", "password": "password123"}).json()[
        "access_token"
    ]
    headers = {"Authorization": f"Bearer {token}"}
    client.put(
        "/api/v1/profile",
        headers=headers,
        json={"data": {"summary": "Python engineer", "skills": ["Python", "FastAPI"]}},
    )
    job = client.post(
        "/api/v1/jobs/normalize",
        headers=headers,
        json={"url": "https://jobs.test/e2e", "content": "Python FastAPI", "title": "Python Engineer"},
    )
    report = client.post("/api/v1/matching", headers=headers, json={"job_ids": [job.json()["id"]]}).json()
    detail = client.get(f"/api/v1/matching/reports/{report['report_id']}", headers=headers).json()
    cv = client.post("/api/v1/cv/tailor", headers=headers, json={"matching_id": detail["results"][0]["id"]})
    for _ in range(20):
        status = client.get(f"/api/v1/processing-jobs/{cv.json()['id']}", headers=headers)
        if status.json().get("result_id"):
            break
        time.sleep(0.01)
    assert status.json().get("result_id")
    assert client.get(f"/api/v1/cv/{status.json()['result_id']}/download", headers=headers).status_code == 200
