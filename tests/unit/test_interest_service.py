from datetime import datetime, timedelta, timezone

import pytest

from jobs.interest_service import (
    contains_pattern,
    ensure_interest,
    list_interests,
    release_interest,
    remove_interest,
)
from shared.models import Job, JobInterest, User


def _user(session, email):
    user = User(email=email, hashed_password="hash")
    session.add(user)
    session.flush()
    return user


def _job(session, url, **fields):
    job = Job(url=url, title=fields.pop("title", "Engineer"), status=fields.pop("status", "completed"), **fields)
    session.add(job)
    session.flush()
    return job


def test_contains_pattern_strips_and_escapes_wildcards():
    assert contains_pattern("  Acme  ") == "%Acme%"
    assert contains_pattern("100%_x\\") == "%100\\%\\_x\\\\%"


def test_ensure_interest_creates_once_and_returns_existing(database_session):
    user = _user(database_session, "a@example.com")
    job = _job(database_session, "https://jobs.test/svc-1")

    first, created = ensure_interest(database_session, user.id, job.id)
    second, created_again = ensure_interest(database_session, user.id, job.id)

    assert created is True
    assert created_again is False
    assert first.id == second.id
    assert database_session.query(JobInterest).count() == 1


def test_ensure_interest_is_per_user(database_session):
    first_user = _user(database_session, "a@example.com")
    second_user = _user(database_session, "b@example.com")
    job = _job(database_session, "https://jobs.test/svc-2")

    first, _ = ensure_interest(database_session, first_user.id, job.id)
    second, created = ensure_interest(database_session, second_user.id, job.id)

    assert created is True
    assert first.id != second.id


def test_ensure_interest_does_not_commit(database_session):
    user = _user(database_session, "a@example.com")
    job = _job(database_session, "https://jobs.test/svc-3")
    database_session.commit()

    ensure_interest(database_session, user.id, job.id)
    database_session.rollback()

    assert database_session.query(JobInterest).count() == 0


@pytest.mark.parametrize("value", ["", "   "])
def test_contains_pattern_blank_matches_everything(value):
    assert contains_pattern(value) == "%%"


def _seed_interests(session, user, count, *, company="Acme"):
    base = datetime(2026, 10, 1, tzinfo=timezone.utc)
    for index in range(count):
        job = _job(
            session, f"https://jobs.test/{user.email}/{company}/{index}", title=f"Job {index}", company=company
        )
        session.add(JobInterest(user_id=user.id, job_id=job.id, created_at=base + timedelta(minutes=index)))
    session.commit()


def _list(session, user, **overrides):
    options = {"title": None, "company": None, "location": None, "page": 1, "limit": 20, **overrides}
    return list_interests(session, user.id, **options)


@pytest.mark.parametrize(
    ("count", "limit", "pages"),
    [(0, 20, 0), (1, 20, 1), (20, 20, 1), (21, 20, 2), (5, 2, 3)],
)
def test_list_interests_reports_total_and_page_size(database_session, count, limit, pages):
    user = _user(database_session, "pages@example.com")
    _seed_interests(database_session, user, count)

    rows, total = _list(database_session, user, limit=limit)

    assert total == count
    assert len(rows) == min(count, limit)
    assert -(-total // limit) == pages


def test_list_interests_is_scoped_to_the_owner(database_session):
    owner = _user(database_session, "owner@example.com")
    other = _user(database_session, "other@example.com")
    _seed_interests(database_session, owner, 2)
    _seed_interests(database_session, other, 3)

    rows, total = _list(database_session, owner)

    assert total == 2
    assert {interest.user_id for interest, _ in rows} == {owner.id}


def test_list_interests_combines_filters_and_returns_job_rows(database_session):
    user = _user(database_session, "filter@example.com")
    _seed_interests(database_session, user, 2, company="Globex")
    _seed_interests(database_session, user, 1, company="Acme")

    rows, total = _list(database_session, user, company="glob", title="job 1")

    assert total == 1
    interest, job = rows[0]
    assert job.company == "Globex"
    assert interest.job_id == job.id


def test_list_interests_orders_equal_timestamps_by_id_descending(database_session):
    user = _user(database_session, "ties@example.com")
    same_time = datetime(2026, 10, 1, tzinfo=timezone.utc)
    for index, interest_id in enumerate(["a", "c", "b"]):
        job = _job(database_session, f"https://jobs.test/ties/{index}")
        database_session.add(JobInterest(id=interest_id, user_id=user.id, job_id=job.id, created_at=same_time))
    database_session.commit()

    rows, _ = _list(database_session, user)

    assert [interest.id for interest, _ in rows] == ["c", "b", "a"]


def test_remove_interest_deletes_only_the_callers_row(database_session):
    owner = _user(database_session, "owner@example.com")
    other = _user(database_session, "other@example.com")
    job = _job(database_session, "https://jobs.test/rm-unit")
    ensure_interest(database_session, owner.id, job.id)
    ensure_interest(database_session, other.id, job.id)
    database_session.commit()

    assert remove_interest(database_session, owner.id, job.id) is True
    assert remove_interest(database_session, owner.id, job.id) is False
    database_session.commit()

    remaining = database_session.query(JobInterest).all()
    assert [interest.user_id for interest in remaining] == [other.id]
    assert database_session.get(Job, job.id) is not None


def test_remove_interest_does_not_commit(database_session):
    user = _user(database_session, "rollback@example.com")
    job = _job(database_session, "https://jobs.test/rm-rollback")
    ensure_interest(database_session, user.id, job.id)
    database_session.commit()

    remove_interest(database_session, user.id, job.id)
    database_session.rollback()

    assert database_session.query(JobInterest).count() == 1


def test_release_interest_reports_whether_a_row_was_removed(database_session):
    user = _user(database_session, "release@example.com")
    job = _job(database_session, "https://jobs.test/release-1")
    ensure_interest(database_session, user.id, job.id)
    database_session.commit()

    assert release_interest(database_session, user.id, job.id) is True
    assert release_interest(database_session, user.id, job.id) is False
    database_session.commit()

    assert database_session.query(JobInterest).count() == 0
    assert database_session.get(Job, job.id) is not None


def test_release_interest_does_not_commit_and_only_affects_the_caller(database_session):
    user = _user(database_session, "release-owner@example.com")
    other = _user(database_session, "release-other@example.com")
    job = _job(database_session, "https://jobs.test/release-2")
    ensure_interest(database_session, user.id, job.id)
    ensure_interest(database_session, other.id, job.id)
    database_session.commit()

    release_interest(database_session, user.id, job.id)
    database_session.rollback()
    assert database_session.query(JobInterest).count() == 2

    release_interest(database_session, user.id, job.id)
    database_session.commit()
    assert [interest.user_id for interest in database_session.query(JobInterest).all()] == [other.id]
