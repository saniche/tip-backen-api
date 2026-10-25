from datetime import datetime, timezone

import pytest
from sqlalchemy import event

import applications.application_service as application_service
from shared.database import testing_engine
from shared.models import (
    ApplicationJournal,
    ApplicationStatus,
    ApplicationStatusHistory,
    Job,
    JobInterest,
    User,
)
from shared.schemas import ApplicationCreate, ApplicationStatusUpdate


def _user(session, email):
    user = User(email=email, hashed_password="hash")
    session.add(user)
    session.flush()
    return user


def _job(session, url, **fields):
    job = Job(
        url=url,
        title=fields.pop("title", "Engineer"),
        company=fields.pop("company", "Acme"),
        location=fields.pop("location", "Remote"),
        status=fields.pop("status", "completed"),
        **fields,
    )
    session.add(job)
    session.flush()
    return job


def _entry(session, user_id, job_id, *, application_id, created_at):
    application = ApplicationJournal(
        id=application_id,
        user_id=user_id,
        job_id=job_id,
        status=ApplicationStatus.NOT_STARTED,
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(application)
    session.flush()
    session.add(
        ApplicationStatusHistory(
            application_id=application.id,
            date=created_at,
            status=ApplicationStatus.NOT_STARTED,
        )
    )
    session.flush()
    return application


class _StatementRecorder:
    def __init__(self):
        self.statements = []

    def __enter__(self):
        event.listen(testing_engine, "before_cursor_execute", self._record)
        return self

    def __exit__(self, *exc):
        event.remove(testing_engine, "before_cursor_execute", self._record)

    def _record(self, conn, cursor, statement, parameters, context, executemany):
        self.statements.append(statement.lower())


def test_list_filters_counts_orders_and_pages_in_database(database_session):
    user = _user(database_session, "service-list@example.com")
    other_user = _user(database_session, "service-list-other@example.com")
    base_time = datetime(2026, 10, 1, tzinfo=timezone.utc)
    for index in range(30):
        job = _job(
            database_session,
            f"https://jobs.test/service-list/{index}",
            title=f"Python Engineer {index}",
            company="Acme",
            location="Toronto",
        )
        _entry(
            database_session,
            user.id,
            job.id,
            application_id=f"application-{index:02}",
            created_at=base_time.replace(minute=index),
        )
    other_job = _job(database_session, "https://jobs.test/service-list/other", title="Private")
    _entry(database_session, other_user.id, other_job.id, application_id="other-application", created_at=base_time)
    database_session.commit()

    with _StatementRecorder() as recorder:
        result = application_service.list_applications(
            database_session,
            user.id,
            title="python",
            company="acme",
            location="toronto",
            page=2,
            limit=10,
        )

    assert result["total"] == 30
    assert result["total_pages"] == 3
    assert len(result["items"]) == 10
    assert "application-19" == result["items"][0]["id"]
    page_queries = [
        sql for sql in recorder.statements if "from application_journals" in sql and " limit " in sql
    ]
    count_queries = [sql for sql in recorder.statements if "count(" in sql and "application_journals" in sql]
    assert len(page_queries) == 1
    assert "offset" in page_queries[0]
    assert "application_journals.user_id" in page_queries[0]
    assert "order by application_journals.created_at desc, application_journals.id desc" in page_queries[0]
    assert "like" in page_queries[0]
    assert len(count_queries) == 1
    assert not any("select application_journals" in sql and "limit" not in sql for sql in recorder.statements)


def test_create_rolls_back_journal_and_history_when_interest_release_fails(database_session, monkeypatch):
    user = _user(database_session, "service-create-failure@example.com")
    job = _job(database_session, "https://jobs.test/service-create-failure")
    database_session.add(JobInterest(user_id=user.id, job_id=job.id))
    database_session.commit()

    def fail_after_release(db, user_id, job_id):
        db.query(JobInterest).filter_by(user_id=user_id, job_id=job_id).delete()
        raise RuntimeError("interest release failed")

    monkeypatch.setattr(application_service, "release_interest", fail_after_release)

    with pytest.raises(RuntimeError, match="interest release failed"):
        application_service.create_application(database_session, user.id, ApplicationCreate(jobId=job.id))

    assert database_session.query(ApplicationJournal).filter_by(user_id=user.id, job_id=job.id).count() == 0
    assert database_session.query(ApplicationStatusHistory).count() == 0
    assert database_session.query(JobInterest).filter_by(user_id=user.id, job_id=job.id).count() == 1


def test_status_update_rolls_back_both_status_and_history_on_commit_failure(database_session, monkeypatch):
    user = _user(database_session, "service-status-failure@example.com")
    job = _job(database_session, "https://jobs.test/service-status-failure")
    application = _entry(
        database_session,
        user.id,
        job.id,
        application_id="status-failure",
        created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    database_session.commit()
    original_commit = database_session.commit

    def fail_commit():
        raise RuntimeError("commit failed")

    monkeypatch.setattr(database_session, "commit", fail_commit)

    with pytest.raises(RuntimeError, match="commit failed"):
        application_service.update_application_status(
            database_session,
            user.id,
            application.id,
            ApplicationStatusUpdate(status=ApplicationStatus.INTERVIEW, note="Scheduled"),
        )

    monkeypatch.setattr(database_session, "commit", original_commit)
    database_session.expire_all()
    persisted = database_session.get(ApplicationJournal, application.id)

    assert persisted.status == ApplicationStatus.NOT_STARTED
    assert database_session.query(ApplicationStatusHistory).filter_by(application_id=application.id).count() == 1
