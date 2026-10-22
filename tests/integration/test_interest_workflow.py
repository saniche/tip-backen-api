from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError

import jobs.job_normalizer as job_normalizer
from jobs.interest_service import ensure_interest, release_interest
from main import app
from shared.database import TestingSessionLocal, testing_engine
from shared.llm_structured import StructuredProviderError
from shared.models import Job, JobInterest, User


def _register(client, session, email):
    token = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"}).json()[
        "access_token"
    ]
    return {"Authorization": "Bearer " + token}, session.query(User).filter(User.email == email).one().id


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

    def matching(self, *fragments):
        return [s for s in self.statements if all(fragment in s for fragment in fragments)]


# --- Listing is executed by the database (US1) ---


def test_listing_filters_counts_sorts_and_pages_in_the_database(client, database_session):
    headers, user_id = _register(client, database_session, "paging@example.com")
    base = datetime(2026, 10, 1, tzinfo=timezone.utc)
    for index in range(45):
        job = Job(url=f"https://jobs.test/paging/{index}", title=f"Platform Engineer {index}", company="Acme")
        database_session.add(job)
        database_session.flush()
        database_session.add(JobInterest(user_id=user_id, job_id=job.id, created_at=base + timedelta(minutes=index)))
    database_session.commit()

    with _StatementRecorder() as recorder:
        response = client.get("/api/v1/jobs/interests?company=acme&limit=10&page=2", headers=headers)

    body = response.json()
    assert body["total"] == 45
    assert body["totalPages"] == 5
    assert len(body["items"]) == 10
    page_statements = recorder.matching("from job_interests", "limit")
    assert len(page_statements) == 1
    assert "offset" in page_statements[0]
    assert "order by job_interests.created_at desc, job_interests.id desc" in page_statements[0]
    assert "job_interests.user_id" in page_statements[0]
    assert "like" in page_statements[0]
    assert len(recorder.matching("count(", "job_interests")) == 1
    assert not recorder.matching("from jobs where")


# --- Duplicate prevention (US2) ---


def _completed_job(session, url):
    job = Job(url=url, title="Engineer", status="completed")
    session.add(job)
    session.commit()
    return job.id


def test_database_rejects_duplicate_user_job_interest(database_session):
    user = User(email="dup@example.com", hashed_password="hash")
    database_session.add(user)
    job_id = _completed_job(database_session, "https://jobs.test/dup")
    database_session.add(JobInterest(user_id=user.id, job_id=job_id))
    database_session.commit()

    database_session.add(JobInterest(user_id=user.id, job_id=job_id))
    with pytest.raises(IntegrityError):
        database_session.commit()


def test_concurrent_add_resolves_to_the_existing_interest(client, database_session, monkeypatch):
    headers, user_id = _register(client, database_session, "race@example.com")
    job_id = _completed_job(database_session, "https://jobs.test/race")

    real_ensure = job_normalizer.ensure_interest
    calls = []

    def racing_ensure(db, requested_user_id, requested_job_id):
        if calls:
            return real_ensure(db, requested_user_id, requested_job_id)
        calls.append(True)
        competitor = TestingSessionLocal()
        competitor.add(JobInterest(user_id=requested_user_id, job_id=requested_job_id))
        competitor.commit()
        competitor.close()
        db.add(JobInterest(user_id=requested_user_id, job_id=requested_job_id))
        db.flush()

    monkeypatch.setattr(job_normalizer, "ensure_interest", racing_ensure)

    response = client.post(f"/api/v1/jobs/{job_id}/interest", headers=headers)

    assert response.status_code == 201
    assert response.json()["status"] == "existing"
    interests = database_session.query(JobInterest).filter(JobInterest.user_id == user_id).all()
    assert len(interests) == 1
    assert response.json()["id"] == interests[0].id


# --- Journal integration: interest release is atomic with the caller's write (US4) ---


@pytest.fixture
def journal(database_session):
    """Stand-in for the future Application Journal's persistence, sharing the caller's transaction."""
    database_session.execute(text("CREATE TABLE test_journal (id TEXT PRIMARY KEY, user_id TEXT, job_id TEXT)"))
    database_session.commit()
    yield
    database_session.rollback()
    database_session.execute(text("DROP TABLE test_journal"))
    database_session.commit()


def _journal_rows(session):
    return session.execute(text("SELECT id FROM test_journal")).scalars().all()


def _create_application(db, entry_id, user_id, job_id, *, release=release_interest):
    """What the journal does: write the entry and release the interest in one unit of work."""
    db.execute(
        text("INSERT INTO test_journal (id, user_id, job_id) VALUES (:id, :user_id, :job_id)"),
        {"id": entry_id, "user_id": user_id, "job_id": job_id},
    )
    release(db, user_id, job_id)


def _interested_user(session, email, url):
    user = User(email=email, hashed_password="hash")
    session.add(user)
    session.flush()
    job = Job(url=url, title="Engineer", status="completed")
    session.add(job)
    session.flush()
    ensure_interest(session, user.id, job.id)
    session.commit()
    return user.id, job.id


def test_release_interest_is_atomic_with_journal_write(database_session, journal):
    user_id, job_id = _interested_user(database_session, "journal-ok@example.com", "https://jobs.test/journal-ok")
    other = User(email="journal-other@example.com", hashed_password="hash")
    database_session.add(other)
    database_session.flush()
    ensure_interest(database_session, other.id, job_id)
    database_session.commit()

    _create_application(database_session, "entry-1", user_id, job_id)
    database_session.commit()

    assert _journal_rows(database_session) == ["entry-1"]
    remaining = database_session.query(JobInterest).all()
    assert [interest.user_id for interest in remaining] == [other.id]
    assert database_session.get(Job, job_id) is not None


def test_failed_journal_write_keeps_the_interest(database_session, journal):
    user_id, job_id = _interested_user(database_session, "journal-fail@example.com", "https://jobs.test/journal-fail")
    _create_application(database_session, "entry-dup", user_id, job_id)
    database_session.commit()
    ensure_interest(database_session, user_id, job_id)
    database_session.commit()

    with pytest.raises(IntegrityError):
        _create_application(database_session, "entry-dup", user_id, job_id)
    database_session.rollback()

    assert _journal_rows(database_session) == ["entry-dup"]
    assert database_session.query(JobInterest).count() == 1


def test_failed_release_prevents_the_journal_entry(database_session, journal):
    user_id, job_id = _interested_user(
        database_session, "journal-release-fail@example.com", "https://jobs.test/journal-release-fail"
    )

    def broken_release(*args, **kwargs):
        raise RuntimeError("release failed")

    with pytest.raises(RuntimeError):
        _create_application(database_session, "entry-2", user_id, job_id, release=broken_release)
    database_session.rollback()

    assert _journal_rows(database_session) == []
    assert database_session.query(JobInterest).count() == 1


def test_application_without_an_interest_still_succeeds(database_session, journal):
    user_id, job_id = _interested_user(database_session, "journal-none@example.com", "https://jobs.test/journal-none")
    release_interest(database_session, user_id, job_id)
    database_session.commit()

    _create_application(database_session, "entry-3", user_id, job_id)
    database_session.commit()

    assert _journal_rows(database_session) == ["entry-3"]
    assert database_session.query(JobInterest).count() == 0
    assert database_session.get(Job, job_id) is not None


# --- Automatic interest after normalization (US3) ---


def _submit(client, headers, url="https://jobs.test/auto", **extra):
    return client.post(
        "/api/v1/jobs/normalize", headers=headers, json={"url": url, "content": "Python Engineer", **extra}
    )


def _interest_job_ids(client, headers):
    return [item["jobId"] for item in client.get("/api/v1/jobs/interests", headers=headers).json()["items"]]


def test_successful_normalization_creates_one_interest_for_the_submitter(client, database_session):
    headers, user_id = _register(client, database_session, "auto@example.com")

    submitted = _submit(client, headers)

    assert submitted.status_code == 202
    job_id = submitted.json()["id"]
    assert client.get(f"/api/v1/processing-jobs/{submitted.json()['processing_job_id']}", headers=headers).json()[
        "status"
    ] == "done"
    assert _interest_job_ids(client, headers) == [job_id]
    assert database_session.query(JobInterest).filter(JobInterest.user_id == user_id).count() == 1


def test_resubmission_by_the_same_user_does_not_duplicate_the_interest(client, database_session):
    headers, _ = _register(client, database_session, "repeat@example.com")

    first = _submit(client, headers, "https://jobs.test/repeat")
    second = _submit(client, headers, "https://jobs.test/repeat")
    third = _submit(client, headers, "https://jobs.test/repeat")

    assert second.json()["status"] == "existing"
    assert third.json()["status"] == "existing"
    assert _interest_job_ids(client, headers) == [first.json()["id"]]
    assert database_session.query(Job).count() == 1
    assert database_session.query(JobInterest).count() == 1


def test_second_user_submitting_the_same_url_gets_their_own_interest(client, database_session):
    first_headers, _ = _register(client, database_session, "first@example.com")
    second_headers, _ = _register(client, database_session, "second@example.com")

    first = _submit(client, first_headers, "https://jobs.test/shared")
    second = _submit(client, second_headers, "https://jobs.test/shared")

    body = second.json()
    assert (body["id"], body["status"]) == (first.json()["id"], "existing")
    assert _interest_job_ids(client, first_headers) == [first.json()["id"]]
    assert _interest_job_ids(client, second_headers) == [first.json()["id"]]
    assert database_session.query(Job).count() == 1
    assert database_session.query(JobInterest).count() == 2


def test_failed_normalization_creates_no_interest(client, database_session, monkeypatch):
    headers, _ = _register(client, database_session, "norm-fail@example.com")

    async def fail(*args, **kwargs):
        raise StructuredProviderError("provider unavailable")

    monkeypatch.setattr(job_normalizer, "normalize_job_content", fail)
    submitted = _submit(client, headers, "https://jobs.test/norm-fail", title="Engineer")

    status = client.get(f"/api/v1/processing-jobs/{submitted.json()['processing_job_id']}", headers=headers).json()
    assert status["status"] == "failed"
    assert database_session.query(JobInterest).count() == 0
    assert _interest_job_ids(client, headers) == []


def test_interest_creation_failure_fails_the_normalization_workflow(client, database_session, monkeypatch):
    headers, _ = _register(client, database_session, "interest-fail@example.com")

    def broken_ensure(*args, **kwargs):
        raise RuntimeError("interest write failed")

    monkeypatch.setattr(job_normalizer, "ensure_interest", broken_ensure)
    submitted = _submit(client, headers, "https://jobs.test/interest-fail", title="Engineer").json()

    status = client.get(f"/api/v1/processing-jobs/{submitted['processing_job_id']}", headers=headers).json()
    database_session.expire_all()
    assert status["status"] == "failed"
    assert status["error"] == "Job normalization failed"
    assert database_session.get(Job, submitted["id"]).status == "failed"
    assert database_session.query(JobInterest).count() == 0


@pytest.mark.parametrize("status", ["pending", "processing", "failed"])
def test_resubmitting_a_job_that_is_not_normalized_creates_no_interest(client, database_session, status):
    headers, _ = _register(client, database_session, f"inflight-{status}@example.com")
    job = Job(url=f"https://jobs.test/inflight-{status}", title="Engineer", status=status)
    database_session.add(job)
    database_session.commit()

    response = _submit(client, headers, job.url)

    body = response.json()
    assert (body["id"], body["status"]) == (job.id, "existing")
    assert database_session.query(JobInterest).count() == 0


def test_interest_failure_for_an_existing_normalized_job_is_not_reported_as_success(
    client, database_session, monkeypatch
):
    headers, _ = _register(client, database_session, "existing-fail@example.com")
    job = Job(url="https://jobs.test/existing-fail", title="Engineer", status="completed")
    database_session.add(job)
    database_session.commit()

    def broken_ensure(*args, **kwargs):
        raise RuntimeError("interest write failed")

    monkeypatch.setattr(job_normalizer, "ensure_interest", broken_ensure)
    failing_client = TestClient(app, raise_server_exceptions=False)

    response = failing_client.post(
        "/api/v1/jobs/normalize", headers=headers, json={"url": job.url, "content": "Python Engineer"}
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert database_session.query(JobInterest).count() == 0
