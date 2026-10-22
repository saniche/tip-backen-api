from datetime import datetime, timedelta, timezone

import pytest

from shared.models import Job, JobInterest, User

BASE_TIME = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def register(client, session, email):
    token = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"}).json()[
        "access_token"
    ]
    user = session.query(User).filter(User.email == email).one()
    return {"Authorization": "Bearer " + token}, user.id


def make_job(session, url, *, title="Engineer", company="Acme", location="Remote", status="completed", **fields):
    job = Job(url=url, title=title, company=company, location=location, status=status, **fields)
    session.add(job)
    session.commit()
    return job.id


def make_interest(session, user_id, job_id, *, minutes=0, interest_id=None):
    interest = JobInterest(user_id=user_id, job_id=job_id, created_at=BASE_TIME + timedelta(minutes=minutes))
    if interest_id:
        interest.id = interest_id
    session.add(interest)
    session.commit()
    return interest.id


def titles(response):
    return [item["job"]["title"] for item in response.json()["items"]]


# --- Listing (US1) ---


def test_list_interests_requires_authentication(client):
    assert client.get("/api/v1/jobs/interests").status_code == 401


def test_list_interests_returns_only_callers_interests_with_job_header(client, database_session):
    headers, user_id = register(client, database_session, "owner@example.com")
    other_headers, other_id = register(client, database_session, "other@example.com")
    job_id = make_job(
        database_session,
        "https://jobs.test/list-1",
        title="Python Engineer",
        company="Acme",
        location="Toronto",
        source="Indeed",
        posting_date="2026-09-30",
    )
    other_job = make_job(database_session, "https://jobs.test/list-2", title="Other Job")
    interest_id = make_interest(database_session, user_id, job_id)
    make_interest(database_session, other_id, other_job)

    body = client.get("/api/v1/jobs/interests", headers=headers).json()

    assert body["total"] == 1
    assert body["page"] == 1
    assert body["limit"] == 20
    assert body["totalPages"] == 1
    item = body["items"][0]
    assert set(item) == {"id", "jobId", "createdAt", "job"}
    assert item["id"] == interest_id
    assert item["jobId"] == job_id
    assert item["createdAt"]
    assert item["job"] == {
        "id": job_id,
        "title": "Python Engineer",
        "company": "Acme",
        "location": "Toronto",
        "url": "https://jobs.test/list-1",
        "source": "Indeed",
        "postingDate": "2026-09-30",
    }
    other_body = client.get("/api/v1/jobs/interests", headers=other_headers).json()
    assert titles(client.get("/api/v1/jobs/interests", headers=other_headers)) == ["Other Job"]
    assert other_body["total"] == 1


def test_list_interests_returns_null_for_missing_optional_header_fields(client, database_session):
    headers, user_id = register(client, database_session, "nulls@example.com")
    job = Job(title="Bare Job", status="completed")
    database_session.add(job)
    database_session.commit()
    make_interest(database_session, user_id, job.id)

    item = client.get("/api/v1/jobs/interests", headers=headers).json()["items"][0]

    assert item["job"]["company"] is None
    assert item["job"]["location"] is None
    assert item["job"]["url"] is None
    assert item["job"]["source"] is None
    assert item["job"]["postingDate"] is None


def test_list_interests_orders_newest_first_with_stable_tie_break(client, database_session):
    headers, user_id = register(client, database_session, "order@example.com")
    old = make_job(database_session, "https://jobs.test/o1", title="Old")
    new = make_job(database_session, "https://jobs.test/o2", title="New")
    tie_a = make_job(database_session, "https://jobs.test/o3", title="Tie A")
    tie_b = make_job(database_session, "https://jobs.test/o4", title="Tie B")
    make_interest(database_session, user_id, old, minutes=0)
    make_interest(database_session, user_id, new, minutes=10)
    make_interest(database_session, user_id, tie_a, minutes=5, interest_id="interest-a")
    make_interest(database_session, user_id, tie_b, minutes=5, interest_id="interest-b")

    assert titles(client.get("/api/v1/jobs/interests", headers=headers)) == ["New", "Tie B", "Tie A", "Old"]


def test_list_interests_filters_combine_with_and_and_ignore_case(client, database_session):
    headers, user_id = register(client, database_session, "filters@example.com")
    jobs = [
        ("Senior Python Engineer", "Acme Corp", "Toronto, ON"),
        ("Senior Java Engineer", "Acme Corp", "Remote"),
        ("Python Analyst", "Globex", "Toronto, ON"),
    ]
    for index, (title, company, location) in enumerate(jobs):
        job_id = make_job(
            database_session, f"https://jobs.test/f{index}", title=title, company=company, location=location
        )
        make_interest(database_session, user_id, job_id, minutes=index)

    def listed(query):
        return set(titles(client.get(f"/api/v1/jobs/interests?{query}", headers=headers)))

    assert listed("company=acme") == {"Senior Python Engineer", "Senior Java Engineer"}
    assert listed("title=PYTHON") == {"Senior Python Engineer", "Python Analyst"}
    assert listed("location=toronto") == {"Senior Python Engineer", "Python Analyst"}
    assert listed("company=acme&title=python&location=toronto") == {"Senior Python Engineer"}
    assert listed("company=acme&location=nowhere") == set()
    assert len(listed("company=%20%20")) == 3


def test_list_interests_treats_wildcards_literally(client, database_session):
    headers, user_id = register(client, database_session, "wild@example.com")
    for index, company in enumerate(["100% Remote Inc", "1000 Remote Inc", "A_B Corp", "AXB Corp"]):
        job_id = make_job(database_session, f"https://jobs.test/w{index}", title=company, company=company)
        make_interest(database_session, user_id, job_id, minutes=index)

    assert titles(client.get("/api/v1/jobs/interests?company=100%25", headers=headers)) == ["100% Remote Inc"]
    assert titles(client.get("/api/v1/jobs/interests?company=A_B", headers=headers)) == ["A_B Corp"]


def test_list_interests_paginates_with_metadata(client, database_session):
    headers, user_id = register(client, database_session, "pages@example.com")
    for index in range(5):
        job_id = make_job(database_session, f"https://jobs.test/p{index}", title=f"Job {index}")
        make_interest(database_session, user_id, job_id, minutes=index)

    first = client.get("/api/v1/jobs/interests?page=1&limit=2", headers=headers).json()
    second = client.get("/api/v1/jobs/interests?page=2&limit=2", headers=headers).json()
    third = client.get("/api/v1/jobs/interests?page=3&limit=2", headers=headers).json()

    assert [i["job"]["title"] for i in first["items"]] == ["Job 4", "Job 3"]
    assert [i["job"]["title"] for i in second["items"]] == ["Job 2", "Job 1"]
    assert [i["job"]["title"] for i in third["items"]] == ["Job 0"]
    for body, page in ((first, 1), (second, 2), (third, 3)):
        assert body["total"] == 5
        assert body["limit"] == 2
        assert body["totalPages"] == 3
        assert body["page"] == page


def test_list_interests_page_beyond_last_and_no_matches_are_empty(client, database_session):
    headers, user_id = register(client, database_session, "empty@example.com")
    job_id = make_job(database_session, "https://jobs.test/e1")
    make_interest(database_session, user_id, job_id)

    beyond = client.get("/api/v1/jobs/interests?page=9", headers=headers)
    none = client.get("/api/v1/jobs/interests?title=zzz", headers=headers)

    assert beyond.status_code == 200
    assert beyond.json()["items"] == []
    assert beyond.json()["total"] == 1
    assert beyond.json()["totalPages"] == 1
    assert none.json() == {"items": [], "total": 0, "page": 1, "limit": 20, "totalPages": 0}


@pytest.mark.parametrize("query", ["page=0", "limit=0", "limit=101", "page=abc"])
def test_list_interests_rejects_invalid_pagination(client, database_session, query):
    headers, _ = register(client, database_session, "invalid@example.com")

    response = client.get(f"/api/v1/jobs/interests?{query}", headers=headers)

    assert response.status_code == 422


def test_list_interests_allows_maximum_page_size(client, database_session):
    headers, _ = register(client, database_session, "max@example.com")

    assert client.get("/api/v1/jobs/interests?limit=100", headers=headers).status_code == 200


def test_list_interests_reflects_job_updates_without_changing_the_interest(client, database_session):
    headers, user_id = register(client, database_session, "reflect@example.com")
    job_id = make_job(database_session, "https://jobs.test/r1", title="Before")
    make_interest(database_session, user_id, job_id)

    database_session.get(Job, job_id).title = "After"
    database_session.commit()

    assert titles(client.get("/api/v1/jobs/interests", headers=headers)) == ["After"]


# --- Add and remove (US2) ---


def test_add_interest_is_idempotent(client, database_session):
    headers, _ = register(client, database_session, "add@example.com")
    job_id = make_job(database_session, "https://jobs.test/a1")

    first = client.post(f"/api/v1/jobs/{job_id}/interest", headers=headers)
    second = client.post(f"/api/v1/jobs/{job_id}/interest", headers=headers)

    assert first.status_code == 201
    assert first.json()["status"] == "created"
    assert second.status_code == 201
    assert second.json() == {"id": first.json()["id"], "status": "existing"}
    assert client.get("/api/v1/jobs/interests", headers=headers).json()["total"] == 1


def test_add_interest_unknown_job_is_not_found(client, database_session):
    headers, _ = register(client, database_session, "unknown@example.com")

    response = client.post("/api/v1/jobs/missing-job/interest", headers=headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert database_session.query(JobInterest).count() == 0


@pytest.mark.parametrize("status", ["pending", "processing", "failed"])
def test_add_interest_requires_normalized_job(client, database_session, status):
    headers, _ = register(client, database_session, f"status-{status}@example.com")
    job_id = make_job(database_session, f"https://jobs.test/s-{status}", status=status)

    response = client.post(f"/api/v1/jobs/{job_id}/interest", headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
    assert database_session.query(JobInterest).count() == 0


def test_add_and_remove_interest_require_authentication(client, database_session):
    job_id = make_job(database_session, "https://jobs.test/auth1")

    assert client.post(f"/api/v1/jobs/{job_id}/interest").status_code == 401
    assert client.delete(f"/api/v1/jobs/{job_id}/interest").status_code == 401


def test_remove_interest_keeps_the_job(client, database_session):
    headers, user_id = register(client, database_session, "remove@example.com")
    job_id = make_job(database_session, "https://jobs.test/rm1")
    make_interest(database_session, user_id, job_id)

    removed = client.delete(f"/api/v1/jobs/{job_id}/interest", headers=headers)

    assert removed.status_code == 204
    assert removed.content == b""
    assert client.get("/api/v1/jobs/interests", headers=headers).json()["total"] == 0
    assert client.get(f"/api/v1/jobs/{job_id}", headers=headers).status_code == 200


def test_remove_missing_interest_is_not_found(client, database_session):
    headers, _ = register(client, database_session, "norow@example.com")
    job_id = make_job(database_session, "https://jobs.test/rm2")

    missing_interest = client.delete(f"/api/v1/jobs/{job_id}/interest", headers=headers)
    missing_job = client.delete("/api/v1/jobs/missing-job/interest", headers=headers)

    assert missing_interest.status_code == 404
    assert missing_interest.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert missing_job.status_code == 404


def test_users_cannot_remove_or_see_each_others_interests(client, database_session):
    owner_headers, owner_id = register(client, database_session, "own@example.com")
    other_headers, other_id = register(client, database_session, "intruder@example.com")
    job_id = make_job(database_session, "https://jobs.test/iso1")
    owner_interest = make_interest(database_session, owner_id, job_id)

    denied = client.delete(f"/api/v1/jobs/{job_id}/interest", headers=other_headers)

    assert denied.status_code == 404
    assert [i["id"] for i in client.get("/api/v1/jobs/interests", headers=owner_headers).json()["items"]] == [
        owner_interest
    ]
    assert client.get("/api/v1/jobs/interests", headers=other_headers).json()["total"] == 0

    other_interest = client.post(f"/api/v1/jobs/{job_id}/interest", headers=other_headers).json()["id"]
    assert other_interest != owner_interest
    assert client.delete(f"/api/v1/jobs/{job_id}/interest", headers=other_headers).status_code == 204
    assert client.get("/api/v1/jobs/interests", headers=owner_headers).json()["total"] == 1
