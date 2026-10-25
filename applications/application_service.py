from datetime import datetime, timedelta, timezone
from math import ceil

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from jobs.interest_service import contains_pattern, release_interest
from shared.models import (
    ApplicationJournal,
    ApplicationStatus,
    ApplicationStatusHistory,
    Job,
)
from shared.schemas import ApplicationCreate, ApplicationFieldsUpdate, ApplicationStatusUpdate


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _status_value(status: ApplicationStatus) -> str:
    return status.value if isinstance(status, ApplicationStatus) else str(status)


def _is_duplicate_application(error: IntegrityError) -> bool:
    original = error.orig
    diagnostic = getattr(original, "diag", None)
    if getattr(diagnostic, "constraint_name", None) == "uq_application_journal_user_job":
        return True
    message = str(original).lower()
    return "uq_application_journal_user_job" in message or (
        "application_journals.user_id" in message and "application_journals.job_id" in message
    )


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Application not found")


def _application_item(
    application: ApplicationJournal,
    job: Job,
    history: list[ApplicationStatusHistory],
) -> dict:
    return {
        "id": application.id,
        "job_id": application.job_id,
        "recruiter_info": application.recruiter_info,
        "contact_date": application.contact_date,
        "follow_up_date": application.follow_up_date,
        "work_authorization_discussed": application.work_authorization_discussed,
        "notes": application.notes,
        "status": _status_value(application.status),
        "history": [
            {
                "date": _utc(event.date),
                "note": event.note,
                "status": _status_value(event.status),
            }
            for event in history
        ],
        "created_at": _utc(application.created_at),
        "updated_at": _utc(application.updated_at),
        "job": {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
            "source": job.source,
            "posting_date": job.posting_date,
        },
    }


def _get_owned_application(
    db: Session,
    user_id: str,
    application_id: str,
    *,
    lock: bool = False,
) -> tuple[ApplicationJournal, Job]:
    query = (
        select(ApplicationJournal, Job)
        .join(Job, Job.id == ApplicationJournal.job_id)
        .where(ApplicationJournal.id == application_id, ApplicationJournal.user_id == user_id)
    )
    if lock:
        query = query.with_for_update(of=ApplicationJournal)
    row = db.execute(query).one_or_none()
    if row is None:
        raise _not_found()
    return row


def _history_for(db: Session, application_id: str) -> list[ApplicationStatusHistory]:
    return db.execute(
        select(ApplicationStatusHistory)
        .where(ApplicationStatusHistory.application_id == application_id)
        .order_by(ApplicationStatusHistory.date.asc(), ApplicationStatusHistory.id.asc())
    ).scalars().all()


def create_application(db: Session, user_id: str, payload: ApplicationCreate) -> dict:
    job = db.get(Job, payload.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=409, detail="Job normalization is not complete")
    existing_id = db.scalar(
        select(ApplicationJournal.id).where(
            ApplicationJournal.user_id == user_id,
            ApplicationJournal.job_id == payload.job_id,
        )
    )
    if existing_id is not None:
        raise HTTPException(status_code=409, detail="Application journal entry already exists for this job")

    timestamp = _now()
    application = ApplicationJournal(
        user_id=user_id,
        job_id=payload.job_id,
        recruiter_info=payload.recruiter_info.model_dump() if payload.recruiter_info is not None else None,
        contact_date=payload.contact_date,
        follow_up_date=payload.follow_up_date,
        work_authorization_discussed=payload.work_authorization_discussed,
        notes=payload.notes,
        status=ApplicationStatus.NOT_STARTED,
        created_at=timestamp,
        updated_at=timestamp,
    )
    try:
        db.add(application)
        db.flush()
        initial_history = ApplicationStatusHistory(
            application_id=application.id,
            date=timestamp,
            note=None,
            status=ApplicationStatus.NOT_STARTED,
        )
        db.add(initial_history)
        db.flush()
        release_interest(db, user_id, payload.job_id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _is_duplicate_application(exc):
            raise HTTPException(
                status_code=409,
                detail="Application journal entry already exists for this job",
            ) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return _application_item(application, job, [initial_history])


def get_application(db: Session, user_id: str, application_id: str) -> dict:
    application, job = _get_owned_application(db, user_id, application_id)
    return _application_item(application, job, _history_for(db, application.id))


def list_applications(
    db: Session,
    user_id: str,
    *,
    title: str | None,
    company: str | None,
    location: str | None,
    page: int,
    limit: int,
) -> dict:
    conditions = [ApplicationJournal.user_id == user_id]
    for value, column in ((title, Job.title), (company, Job.company), (location, Job.location)):
        if value and value.strip():
            conditions.append(column.ilike(contains_pattern(value), escape="\\"))

    total = db.scalar(
        select(func.count(ApplicationJournal.id)).join(Job, Job.id == ApplicationJournal.job_id).where(*conditions)
    ) or 0
    rows = db.execute(
        select(ApplicationJournal, Job)
        .join(Job, Job.id == ApplicationJournal.job_id)
        .where(*conditions)
        .order_by(ApplicationJournal.created_at.desc(), ApplicationJournal.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    application_ids = [application.id for application, _ in rows]
    history_by_application: dict[str, list[ApplicationStatusHistory]] = {key: [] for key in application_ids}
    if application_ids:
        events = db.execute(
            select(ApplicationStatusHistory)
            .where(ApplicationStatusHistory.application_id.in_(application_ids))
            .order_by(ApplicationStatusHistory.date.asc(), ApplicationStatusHistory.id.asc())
        ).scalars().all()
        for event in events:
            history_by_application[event.application_id].append(event)

    return {
        "items": [
            _application_item(application, job, history_by_application[application.id])
            for application, job in rows
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": ceil(total / limit) if total else 0,
    }


def update_application_fields(
    db: Session,
    user_id: str,
    application_id: str,
    payload: ApplicationFieldsUpdate,
) -> dict:
    application, job = _get_owned_application(db, user_id, application_id)
    fields = payload.model_dump(exclude_unset=True)
    if "recruiter_info" in fields and payload.recruiter_info is not None:
        fields["recruiter_info"] = payload.recruiter_info.model_dump()
    for field, value in fields.items():
        setattr(application, field, value)
    application.updated_at = _now()
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return _application_item(application, job, _history_for(db, application.id))


def update_application_status(
    db: Session,
    user_id: str,
    application_id: str,
    payload: ApplicationStatusUpdate,
) -> dict:
    application, job = _get_owned_application(db, user_id, application_id, lock=True)
    if application.status == payload.status:
        return _application_item(application, job, _history_for(db, application.id))

    existing_history = _history_for(db, application.id)
    timestamp = _now()
    if existing_history:
        timestamp = max(timestamp, _utc(existing_history[-1].date) + timedelta(microseconds=1))
    history_entry = ApplicationStatusHistory(
        application_id=application.id,
        date=timestamp,
        note=payload.note,
        status=payload.status,
    )
    application.status = payload.status
    application.updated_at = timestamp
    db.add(history_entry)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return _application_item(application, job, _history_for(db, application.id))


def delete_application(db: Session, user_id: str, application_id: str) -> None:
    application, _ = _get_owned_application(db, user_id, application_id)
    db.query(ApplicationStatusHistory).filter_by(application_id=application.id).delete(synchronize_session=False)
    db.delete(application)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
