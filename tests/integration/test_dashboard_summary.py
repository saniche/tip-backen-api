from datetime import date, datetime, timedelta, timezone

import pytest

import dashboard.router as dashboard_router
from shared.models import (
    ApplicationJournal,
    ApplicationStatus,
    CVRequest,
    Job,
    JobInterest,
    MatchReport,
    User,
    UserProfile,
)


def register(client, session, email):
    response = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    assert response.status_code == 201
    user_id = session.query(User).filter_by(email=email).one().id
    return {"Authorization": f"Bearer {response.json()['access_token']}"}, user_id


def test_summary_boundaries_isolation_and_empty_account(client, database_session):
    headers, user_id = register(client, database_session, "dashboard@example.com")
    other_headers, other_id = register(client, database_session, "dashboard-other@example.com")
    empty_headers, _ = register(client, database_session, "dashboard-empty@example.com")
    today = date(2026, 11, 11)
    cases = [
        ("a", ApplicationStatus.APPLIED, today - timedelta(days=1)),
        ("b", ApplicationStatus.OFFERED, today),
        ("c", ApplicationStatus.CONTACTED, today + timedelta(days=1)),
        ("d", ApplicationStatus.INTERVIEW, None),
        ("e", ApplicationStatus.CLOSED, today - timedelta(days=2)),
        ("f", ApplicationStatus.REJECTED, today),
        ("g", ApplicationStatus.ACCEPTED, today),
        ("h", ApplicationStatus.SCREENING, today - timedelta(days=1)),
    ]
    for entry_id, application_status, due_date in cases:
        job = Job(id=f"job-{entry_id}", title=f"Title {entry_id}", company=None if entry_id == "a" else "Acme")
        database_session.add(job)
        database_session.add(ApplicationJournal(
            id=entry_id, user_id=user_id, job_id=job.id, status=application_status, follow_up_date=due_date
        ))
    database_session.add(ApplicationJournal(id="other", user_id=other_id, job_id="job-a", follow_up_date=today))
    database_session.add_all([
        JobInterest(user_id=user_id, job_id="job-a"),
        JobInterest(user_id=other_id, job_id="job-a"),
        MatchReport(user_id=user_id, status="pending"),
        MatchReport(user_id=other_id),
        CVRequest(user_id=user_id, job_ids=[]),
        CVRequest(user_id=other_id),
        UserProfile(user_id=user_id, data={}),
        UserProfile(user_id=user_id, data={}, deleted_at=datetime(2026, 1, 1, tzinfo=timezone.utc)),
        UserProfile(user_id=other_id, data={}),
    ])
    database_session.commit()

    response = client.get("/api/v1/dashboard/summary?today=2026-11-11&follow_up_limit=2", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result["applications"]["total"] == len(cases)
    assert result["applications"]["by_status"] == {
        status.value: sum(1 for _, case_status, _ in cases if case_status == status) for status in ApplicationStatus
    }
    assert result["applications"]["follow_ups_due"] == {
        "count": 3,
        "items": [
            {"id": "a", "job_title": "Title a", "company": None, "follow_up_date": "2026-11-10"},
            {"id": "h", "job_title": "Title h", "company": "Acme", "follow_up_date": "2026-11-10"},
        ],
    }
    assert all(result[key] == {"total": 1} for key in (
        "interests", "matching_reports", "tailoring_requests", "profiles"
    ))
    other = client.get("/api/v1/dashboard/summary?today=2026-11-11", headers=other_headers).json()
    assert other["applications"]["total"] == 1
    assert [item["id"] for item in other["applications"]["follow_ups_due"]["items"]] == ["other"]
    empty = client.get("/api/v1/dashboard/summary?today=2026-11-11", headers=empty_headers).json()
    assert empty["applications"]["total"] == 0
    assert empty["applications"]["by_status"] == {status.value: 0 for status in ApplicationStatus}
    assert empty["applications"]["follow_ups_due"] == {"count": 0, "items": []}
    assert all(empty[key] == {"total": 0} for key in (
        "interests", "matching_reports", "tailoring_requests", "profiles"
    ))
    assert client.get("/api/v1/dashboard/summary").status_code == 401


def test_summary_limit_and_utc_default(client, database_session, monkeypatch):
    headers, user_id = register(client, database_session, "dashboard-limit@example.com")
    for index in range(105):
        job = Job(id=f"limit-job-{index:03}", title="Job")
        database_session.add(job)
        database_session.add(ApplicationJournal(
            id=f"limit-{index:03}", user_id=user_id, job_id=job.id, follow_up_date=date(2026, 11, 11)
        ))
    database_session.commit()

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            assert tz == timezone.utc
            return cls(2026, 11, 11, 23, 59, tzinfo=tz)

    monkeypatch.setattr(dashboard_router, "datetime", FrozenDateTime)
    default = client.get("/api/v1/dashboard/summary", headers=headers).json()["applications"]["follow_ups_due"]
    assert default["count"] == 105
    assert len(default["items"]) == 5
    capped = client.get("/api/v1/dashboard/summary?follow_up_limit=101", headers=headers)
    assert capped.status_code == 200
    assert capped.json()["applications"]["total"] == 105
    assert len(capped.json()["applications"]["follow_ups_due"]["items"]) == 100
    earlier = client.get("/api/v1/dashboard/summary?today=2026-11-10", headers=headers).json()
    assert earlier["applications"]["follow_ups_due"] == {"count": 0, "items": []}


@pytest.mark.parametrize("query", [
    "today=not-a-date", "today=0", "today=2026-11-11T00:00:00", "today=2026-02-30",
    "follow_up_limit=0", "follow_up_limit=abc",
])
def test_summary_rejects_invalid_query(client, database_session, query):
    headers, _ = register(client, database_session, f"invalid-{query.split('=')[0]}-{len(query)}@example.com")
    response = client.get(f"/api/v1/dashboard/summary?{query}", headers=headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
