from datetime import datetime, timedelta, timezone

from models import Job


def test_jobs_are_newest_first_and_saved_date_bounds_work(database_session):
    now = datetime.now(timezone.utc)
    database_session.add_all(
        [
            Job(url="https://jobs.test/old", title="Old", created_at=now - timedelta(days=2)),
            Job(url="https://jobs.test/new", title="New", created_at=now),
        ]
    )
    database_session.commit()

    jobs = database_session.query(Job).order_by(Job.created_at.desc()).all()
    assert [job.title for job in jobs] == ["New", "Old"]
