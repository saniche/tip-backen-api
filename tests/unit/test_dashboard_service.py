from datetime import date, datetime, timezone

from sqlalchemy import event

from dashboard.service import get_dashboard_summary
from shared.database import testing_engine
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


def test_summary_counts_owned_rows_and_uses_fixed_number_of_queries(database_session):
    session = database_session
    owner = User(email="dashboard-unit@example.com", hashed_password="hash")
    other = User(email="dashboard-unit-other@example.com", hashed_password="hash")
    session.add_all([owner, other])
    session.flush()
    jobs = [Job(title=f"Job {index}", company=None) for index in range(111)]
    session.add_all(jobs)
    session.flush()
    for index, job in enumerate(jobs[:110]):
        session.add(ApplicationJournal(
            id=f"entry-{index:03}", user_id=owner.id, job_id=job.id,
            status=list(ApplicationStatus)[index % len(ApplicationStatus)],
            follow_up_date=date(2026, 11, 10),
        ))
    session.add(ApplicationJournal(user_id=other.id, job_id=jobs[110].id, follow_up_date=date(2026, 11, 1)))
    session.add_all([
        JobInterest(user_id=owner.id, job_id=jobs[0].id),
        JobInterest(user_id=other.id, job_id=jobs[0].id),
        MatchReport(user_id=owner.id, status="failed"),
        MatchReport(user_id=other.id),
        CVRequest(user_id=owner.id, job_ids=[], status="failed"),
        CVRequest(user_id=other.id),
        UserProfile(user_id=owner.id, data={}),
        UserProfile(user_id=owner.id, data={}, deleted_at=datetime(2026, 1, 1, tzinfo=timezone.utc)),
        UserProfile(user_id=other.id, data={}),
    ])
    session.commit()
    owner_id = owner.id
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement.lower())

    event.listen(testing_engine, "before_cursor_execute", record)
    try:
        summary = get_dashboard_summary(session, owner_id, date(2026, 11, 11), 5)
    finally:
        event.remove(testing_engine, "before_cursor_execute", record)

    applications = summary["applications"]
    assert applications["total"] == 110
    assert applications["by_status"] == {status.value: 10 for status in ApplicationStatus}
    assert applications["follow_ups_due"]["count"] == 80
    assert [item["id"] for item in applications["follow_ups_due"]["items"]] == [
        "entry-000", "entry-001", "entry-002", "entry-003", "entry-004"
    ]
    assert applications["follow_ups_due"]["items"][0]["company"] is None
    assert summary["interests"]["total"] == 1
    assert summary["matching_reports"]["total"] == 1
    assert summary["tailoring_requests"]["total"] == 1
    assert summary["profiles"]["total"] == 1
    assert len(statements) == 7
    assert all("select" in statement for statement in statements)
    assert sum("from application_journals" in statement for statement in statements) == 3
    assert sum(" join jobs " in statement for statement in statements) == 1


def test_summary_empty_database_has_all_zero_statuses(database_session):
    summary = get_dashboard_summary(database_session, "no-such-user", date(2026, 11, 11), 5)
    assert summary["applications"] == {
        "total": 0,
        "by_status": {status.value: 0 for status in ApplicationStatus},
        "follow_ups_due": {"count": 0, "items": []},
    }
    assert all(summary[key] == {"total": 0} for key in (
        "interests", "matching_reports", "tailoring_requests", "profiles"
    ))
