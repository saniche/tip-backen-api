"""Interest business rules shared by the jobs routes, the normalization workflow, and the Application Journal."""

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from shared.models import Job, JobInterest


def contains_pattern(value: str) -> str:
    escaped = value.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def ensure_interest(db: Session, user_id: str, job_id: str) -> tuple[JobInterest, bool]:
    """Return the user's interest in the job, creating it if absent. Flushes but never commits."""
    existing = db.execute(
        select(JobInterest).where(JobInterest.user_id == user_id, JobInterest.job_id == job_id)
    ).scalar_one_or_none()
    if existing is not None:
        return existing, False
    interest = JobInterest(user_id=user_id, job_id=job_id)
    db.add(interest)
    db.flush()
    return interest, True


def remove_interest(db: Session, user_id: str, job_id: str) -> bool:
    """Delete the user's interest in the job. Returns whether a row was removed; never commits."""
    result = db.execute(delete(JobInterest).where(JobInterest.user_id == user_id, JobInterest.job_id == job_id))
    return result.rowcount > 0


def release_interest(db: Session, user_id: str, job_id: str) -> bool:
    """Release the user's interest in a job as part of the caller's unit of work.

    Intended for the Application Journal: it never commits or rolls back, so creating the application
    entry and releasing the interest succeed or fail together. A missing interest returns False rather
    than raising, and the job and other users' interests are never touched.
    """
    return remove_interest(db, user_id, job_id)


def list_interests(
    db: Session,
    user_id: str,
    *,
    title: str | None,
    company: str | None,
    location: str | None,
    page: int,
    limit: int,
) -> tuple[list[tuple[JobInterest, Job]], int]:
    """Return one page of the user's interests with their jobs, plus the total matching count.

    Ownership, filtering, counting, ordering, and paging are all executed by the database.
    """
    conditions = [JobInterest.user_id == user_id]
    for value, column in ((title, Job.title), (company, Job.company), (location, Job.location)):
        if value and value.strip():
            conditions.append(column.ilike(contains_pattern(value), escape="\\"))

    total = db.scalar(
        select(func.count(JobInterest.id)).join(Job, Job.id == JobInterest.job_id).where(*conditions)
    ) or 0
    rows = db.execute(
        select(JobInterest, Job)
        .join(Job, Job.id == JobInterest.job_id)
        .where(*conditions)
        .order_by(JobInterest.created_at.desc(), JobInterest.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return [(interest, job) for interest, job in rows], total
