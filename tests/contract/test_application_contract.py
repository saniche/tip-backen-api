from datetime import datetime, timedelta, timezone

import pytest

from shared.models import ApplicationJournal, ApplicationStatusHistory, Job, JobInterest, User


def register(client, session, email):
    token = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"}).json()[
        "access_token"
    ]
    return {"Authorization": "Bearer " + token}, session.query(User).filter(User.email == email).one().id


def make_job(session, url, *, title="Engineer", company="Acme", location="Remote", status="completed", **fields):
    job = Job(
        url=url,
        title=title,
        company=company,
        location=location,
        status=status,
        source="CompanyWebsite",
        posting_date="2026-10-01",
        **fields,
    )
    session.add(job)
    session.commit()
    return job.id


def create_application(client, headers, job_id, **fields):
    return client.post("/api/v1/applications", headers=headers, json={"jobId": job_id, **fields})


def test_create_application_initializes_history_without_interest(client, database_session):
    headers, user_id = register(client, database_session, "application-create@example.com")
    job_id = make_job(database_session, "https://jobs.test/application-create", title="Backend Engineer")

    response = create_application(
        client,
        headers,
        job_id,
        recruiterInfo={"name": "A. Recruiter", "email": "recruiter@example.com", "phone": "+1-555-0100"},
        contactDate="2026-10-22",
        workAuthorizationDiscussed=True,
        notes="Application submitted",
    )

    assert response.status_code == 201
    item = response.json()
    assert item["jobId"] == job_id
    assert item["status"] == "NotStarted"
    assert item["history"][0]["status"] == "NotStarted"
    assert item["history"][0]["note"] is None
    assert item["recruiterInfo"] == {
        "name": "A. Recruiter",
        "email": "recruiter@example.com",
        "phone": "+1-555-0100",
    }
    assert item["contactDate"] == "2026-10-22"
    assert item["workAuthorizationDiscussed"] is True
    assert item["job"] == {
        "id": job_id,
        "title": "Backend Engineer",
        "company": "Acme",
        "location": "Remote",
        "url": "https://jobs.test/application-create",
        "source": "CompanyWebsite",
        "postingDate": "2026-10-01",
    }
    assert database_session.query(ApplicationJournal).filter_by(user_id=user_id, job_id=job_id).count() == 1
    assert database_session.query(JobInterest).count() == 0
    assert database_session.query(ApplicationStatusHistory).count() == 1


def test_create_application_releases_only_matching_interest(client, database_session):
    headers, user_id = register(client, database_session, "application-interest@example.com")
    other_headers, other_user_id = register(client, database_session, "application-other@example.com")
    job_id = make_job(database_session, "https://jobs.test/application-interest")
    database_session.add_all(
        [JobInterest(user_id=user_id, job_id=job_id), JobInterest(user_id=other_user_id, job_id=job_id)]
    )
    database_session.commit()

    response = create_application(client, headers, job_id)

    assert response.status_code == 201
    assert database_session.query(JobInterest).filter_by(user_id=user_id, job_id=job_id).count() == 0
    assert database_session.query(JobInterest).filter_by(user_id=other_user_id, job_id=job_id).count() == 1
    assert client.get("/api/v1/applications", headers=other_headers).json()["items"] == []


def test_same_job_can_be_journaled_once_per_user(client, database_session):
    first_headers, first_user_id = register(client, database_session, "application-shared-one@example.com")
    second_headers, second_user_id = register(client, database_session, "application-shared-two@example.com")
    job_id = make_job(database_session, "https://jobs.test/application-shared")

    first = create_application(client, first_headers, job_id)
    second = create_application(client, second_headers, job_id)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert database_session.query(ApplicationJournal).filter_by(job_id=job_id).count() == 2
    assert {
        item.user_id
        for item in database_session.query(ApplicationJournal).filter_by(job_id=job_id).all()
    } == {first_user_id, second_user_id}


def test_create_application_rejects_missing_unnormalized_and_duplicate_jobs(client, database_session):
    headers, _ = register(client, database_session, "application-errors@example.com")
    missing = create_application(client, headers, "missing-job")
    pending_job_id = make_job(database_session, "https://jobs.test/application-pending", status="processing")
    pending = create_application(client, headers, pending_job_id)
    job_id = make_job(database_session, "https://jobs.test/application-duplicate")
    first = create_application(client, headers, job_id)
    duplicate = create_application(client, headers, job_id)

    assert missing.status_code == 404
    assert pending.status_code == 409
    assert first.status_code == 201
    assert duplicate.status_code == 409


def test_application_list_is_owner_scoped_filtered_and_paginated(client, database_session):
    headers, user_id = register(client, database_session, "application-list@example.com")
    other_headers, other_id = register(client, database_session, "application-list-other@example.com")
    jobs = [
        make_job(
            database_session,
            f"https://jobs.test/application-list-{index}",
            title=title,
            company=company,
            location=location,
        )
        for index, (title, company, location) in enumerate(
            [
                ("Senior Python Engineer", "Acme Labs", "Toronto"),
                ("Python Analyst", "Acme Labs", "Remote"),
                ("Java Engineer", "Globex", "Toronto"),
            ]
        )
    ]
    timestamps = [datetime(2026, 10, 1, tzinfo=timezone.utc) + timedelta(minutes=index) for index in range(3)]
    for job_id, created_at in zip(jobs, timestamps):
        database_session.add(
            ApplicationJournal(user_id=user_id, job_id=job_id, status="NotStarted", created_at=created_at)
        )
    other_job = make_job(database_session, "https://jobs.test/application-list-other", title="Secret")
    database_session.add(ApplicationJournal(user_id=other_id, job_id=other_job, status="NotStarted"))
    database_session.commit()

    response = client.get(
        "/api/v1/applications?company=acme&title=python&location=toronto&page=1&limit=1",
        headers=headers,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["limit"] == 1
    assert body["totalPages"] == 1
    assert body["items"][0]["job"]["title"] == "Senior Python Engineer"
    assert client.get("/api/v1/applications", headers=other_headers).json()["items"][0]["job"]["title"] == "Secret"


def test_application_list_orders_newest_first_and_rejects_bad_pagination(client, database_session):
    headers, user_id = register(client, database_session, "application-order@example.com")
    jobs = [
        make_job(database_session, f"https://jobs.test/application-order-{index}", title=f"Job {index}")
        for index in range(3)
    ]
    shared_time = datetime(2026, 10, 1, tzinfo=timezone.utc)
    for index, job_id in enumerate(jobs):
        database_session.add(
            ApplicationJournal(
                id=f"application-{index}",
                user_id=user_id,
                job_id=job_id,
                status="NotStarted",
                created_at=shared_time if index < 2 else shared_time + timedelta(minutes=1),
            )
        )
    database_session.commit()

    response = client.get("/api/v1/applications?limit=2", headers=headers)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == ["application-2", "application-1"]
    assert response.json()["totalPages"] == 2
    assert client.get("/api/v1/applications?page=0", headers=headers).status_code == 422
    assert client.get("/api/v1/applications?limit=101", headers=headers).status_code == 422


def test_application_list_filters_escape_wildcards_and_returns_empty_metadata(client, database_session):
    headers, user_id = register(client, database_session, "application-wildcards@example.com")
    jobs = [
        make_job(
            database_session,
            f"https://jobs.test/application-wildcard-{index}",
            title=title,
            company=company,
            location=location,
        )
        for index, (title, company, location) in enumerate(
            [
                ("Python Engineer", "100% Acme", "Toronto"),
                ("Python Analyst", "1000 Acme", "Remote"),
                ("Java Engineer", "A_B Corp", "Toronto"),
                ("Java Analyst", "AXB Corp", "Remote"),
            ]
        )
    ]
    created_at = datetime.now(timezone.utc)
    for job_id in jobs:
        database_session.add(
            ApplicationJournal(
                user_id=user_id,
                job_id=job_id,
                status="NotStarted",
                created_at=created_at,
            )
        )
    database_session.commit()

    literal_percent = client.get("/api/v1/applications?company=100%25", headers=headers).json()
    literal_underscore = client.get("/api/v1/applications?company=A_B", headers=headers).json()
    empty = client.get("/api/v1/applications?title=not-found", headers=headers).json()
    beyond = client.get("/api/v1/applications?page=9", headers=headers).json()

    assert [item["job"]["company"] for item in literal_percent["items"]] == ["100% Acme"]
    assert [item["job"]["company"] for item in literal_underscore["items"]] == ["A_B Corp"]
    assert empty == {"items": [], "total": 0, "page": 1, "limit": 20, "totalPages": 0}
    assert beyond["items"] == []
    assert beyond["total"] == 4


def test_retrieve_and_update_application_are_owner_scoped(client, database_session):
    headers, user_id = register(client, database_session, "application-owner@example.com")
    other_headers, _ = register(client, database_session, "application-foreign@example.com")
    job_id = make_job(database_session, "https://jobs.test/application-owner")
    entry = create_application(client, headers, job_id).json()

    assert client.get(f"/api/v1/applications/{entry['id']}", headers=other_headers).status_code == 404
    assert client.patch(
        f"/api/v1/applications/{entry['id']}", headers=other_headers, json={"notes": "intrusion"}
    ).status_code == 404
    assert database_session.query(ApplicationJournal).filter_by(user_id=user_id, id=entry["id"]).one().notes is None


def test_editable_updates_preserve_history_and_reject_protected_fields(client, database_session):
    headers, _ = register(client, database_session, "application-update@example.com")
    job_id = make_job(database_session, "https://jobs.test/application-update")
    entry = create_application(client, headers, job_id).json()

    updated = client.patch(
        f"/api/v1/applications/{entry['id']}",
        headers=headers,
        json={
            "recruiterInfo": {"name": "Morgan", "email": None, "phone": None},
            "followUpDate": "2026-10-30",
            "workAuthorizationDiscussed": True,
            "notes": "Waiting for response",
        },
    )
    empty_update = client.patch(f"/api/v1/applications/{entry['id']}", headers=headers, json={})
    protected_update = client.patch(
        f"/api/v1/applications/{entry['id']}", headers=headers, json={"status": "Applied"}
    )
    invalid_recruiter = client.patch(
        f"/api/v1/applications/{entry['id']}", headers=headers, json={"recruiterInfo": {"linkedin": "x"}}
    )
    invalid_boolean = client.patch(
        f"/api/v1/applications/{entry['id']}", headers=headers, json={"workAuthorizationDiscussed": None}
    )
    body = updated.json()

    assert updated.status_code == 200
    assert body["recruiterInfo"]["name"] == "Morgan"
    assert body["recruiterInfo"]["email"] is None
    assert body["followUpDate"] == "2026-10-30"
    assert body["workAuthorizationDiscussed"] is True
    assert body["notes"] == "Waiting for response"
    assert body["status"] == "NotStarted"
    assert body["history"] == entry["history"]
    assert empty_update.status_code == 422
    assert protected_update.status_code == 422
    assert invalid_recruiter.status_code == 422
    assert invalid_boolean.status_code == 422


def test_status_updates_append_only_when_changed(client, database_session):
    headers, _ = register(client, database_session, "application-status@example.com")
    job_id = make_job(database_session, "https://jobs.test/application-status")
    entry = create_application(client, headers, job_id).json()
    status_url = f"/api/v1/applications/{entry['id']}/status"

    changed = client.patch(status_url, headers=headers, json={"status": "Interview", "note": "Scheduled"})
    unchanged = client.patch(status_url, headers=headers, json={"status": "Interview", "note": "Ignored"})
    invalid = client.patch(status_url, headers=headers, json={"status": "Rejected"})

    assert changed.status_code == 200
    assert changed.json()["status"] == "Interview"
    assert [event["status"] for event in changed.json()["history"]] == ["NotStarted", "Interview"]
    assert changed.json()["history"][-1]["note"] == "Scheduled"
    assert unchanged.status_code == 200
    assert len(unchanged.json()["history"]) == 2
    assert unchanged.json()["history"][-1]["note"] == "Scheduled"
    assert invalid.status_code == 422


@pytest.mark.parametrize(
    "status",
    ["Registered", "Applied", "Contacted", "Screening", "Interview", "OnHold", "Closed"],
)
def test_each_supported_application_status_is_accepted(client, database_session, status):
    headers, _ = register(client, database_session, f"application-status-{status}@example.com")
    job_id = make_job(database_session, f"https://jobs.test/application-status-{status}")
    entry = create_application(client, headers, job_id).json()

    response = client.patch(
        f"/api/v1/applications/{entry['id']}/status",
        headers=headers,
        json={"status": status},
    )

    assert response.status_code == 200
    assert response.json()["status"] == status
    assert response.json()["history"][-1]["status"] == status


def test_delete_preserves_job_and_does_not_recreate_interest(client, database_session):
    headers, user_id = register(client, database_session, "application-delete@example.com")
    other_headers, _ = register(client, database_session, "application-delete-other@example.com")
    job_id = make_job(database_session, "https://jobs.test/application-delete")
    database_session.add(JobInterest(user_id=user_id, job_id=job_id))
    database_session.commit()
    entry = create_application(client, headers, job_id).json()

    forbidden = client.delete(f"/api/v1/applications/{entry['id']}", headers=other_headers)
    deleted = client.delete(f"/api/v1/applications/{entry['id']}", headers=headers)
    missing = client.get(f"/api/v1/applications/{entry['id']}", headers=headers)

    assert deleted.status_code == 204
    assert forbidden.status_code == 404
    assert missing.status_code == 404
    assert database_session.get(Job, job_id) is not None
    assert database_session.query(ApplicationStatusHistory).filter_by(application_id=entry["id"]).count() == 0
    assert database_session.query(JobInterest).filter_by(user_id=user_id, job_id=job_id).count() == 0


def test_application_endpoints_require_authentication(client):
    assert client.get("/api/v1/applications").status_code == 401
    assert client.post("/api/v1/applications", json={"jobId": "job"}).status_code == 401
