import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import DateTime, case, cast, delete, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth.security import get_current_user
from jobs.interest_service import contains_pattern, ensure_interest, list_interests, remove_interest
from jobs.job_service import normalize_job_content
from shared.database import SessionLocal, get_db
from shared.models import (
    ApplicationJournal,
    Job,
    JobInterest,
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    User,
)
from shared.schemas import (
    InterestItem,
    InterestJobHeader,
    InterestsPage,
    JobNormalizeOut,
    JobNormalizeRequest,
    NormalizedJobHeader,
    NormalizedJobsResponse,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger("tip-api")

SYSTEM_PROMPT = (
    "You extract structured job posting data from raw text (which may contain one or more distinct "
    "postings, e.g. a scraped search-results page). Extract every distinct posting found. Never invent "
    "details not present in the text — use null for missing optional fields and an empty array for "
    "missing lists."
)


async def _run_job_normalization(
    processing_job_id: str,
    job_id: str,
    client_metadata: dict[str, str | None] | None = None,
) -> None:
    db = SessionLocal()
    try:
        processing_job = db.get(ProcessingJob, processing_job_id)
        job = db.get(Job, job_id)
        if processing_job is None or job is None:
            return
        processing_job.status = ProcessingJobStatus.RUNNING
        job.status = "processing"
        db.commit()
        structured = await normalize_job_content(job.url or "", job.summary or "")
        for field in ("title", "company", "location"):
            if client_metadata and client_metadata.get(field) is not None:
                structured[field] = client_metadata[field]
        for key, value in structured.items():
            database_field = {"requirements": "required", "desirables": "desirable"}.get(key, key)
            setattr(job, database_field, value)
        job.status = "completed"
        processing_job.status = ProcessingJobStatus.DONE
        processing_job.result_id = job.id
        ensure_interest(db, processing_job.user_id, job.id)
        db.commit()
    except Exception:
        logger.exception("Job normalization failed", extra={"processing_job_id": processing_job_id})
        db.rollback()
        if processing_job is not None:
            processing_job = db.get(ProcessingJob, processing_job_id)
            job = db.get(Job, job_id)
            processing_job.status = ProcessingJobStatus.FAILED
            processing_job.error = "Job normalization failed"
            if job is not None:
                job.status = "failed"
            db.commit()
    finally:
        db.close()


@router.post("/normalize", status_code=202, response_model=JobNormalizeOut)
def normalize_job(
    payload: JobNormalizeRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.execute(select(Job).where(Job.url == payload.url)).scalar_one_or_none()
    if existing:
        if existing.status == "completed":
            ensure_interest(db, current_user.id, existing.id)
            db.commit()
        return {"id": existing.id, "status": "existing"}
    job = Job(
        url=payload.url,
        title=payload.title if payload.title is not None else "",
        company=payload.company,
        location=payload.location,
        summary=payload.content,
        submitter_id=current_user.id,
        status="pending",
    )
    db.add(job)
    processing_job = ProcessingJob(user_id=current_user.id, job_type=ProcessingJobType.JOB_NORMALIZE)
    db.add(processing_job)
    db.commit()
    db.refresh(job)
    db.refresh(processing_job)
    background_tasks.add_task(
        _run_job_normalization,
        processing_job.id,
        job.id,
        {"title": payload.title, "company": payload.company, "location": payload.location},
    )
    return {
        "id": job.id,
        "status": "processing",
        "processing_job_id": processing_job.id,
        "title": payload.title,
        "url": job.url,
        "created_at": job.created_at,
    }


@router.get("")
def list_jobs(
    title: str | None = None,
    company: str | None = None,
    location: str | None = None,
    saved_after: str | None = None,
    saved_before: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Job).order_by(desc(Job.created_at)).offset((page - 1) * limit).limit(limit)
    if title:
        query = query.where(Job.title.ilike(f"%{title}%"))
    if company:
        query = query.where(Job.company.ilike(f"%{company}%"))
    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))
    if saved_after:
        query = query.where(Job.created_at >= saved_after)
    if saved_before:
        query = query.where(Job.created_at <= saved_before)
    return [
        {
            "id": job.id,
            "url": job.url,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "created_at": job.created_at,
        }
        for job in db.execute(query).scalars()
    ]


def _posting_date_order_expression(db: Session):
    dialect_name = db.get_bind().dialect.name
    if dialect_name == "sqlite":
        return func.julianday(Job.posting_date)
    if dialect_name == "postgresql":
        valid_date = func.pg_input_is_valid(Job.posting_date, "timestamp with time zone")
        return case(
            (valid_date, cast(Job.posting_date, DateTime(timezone=True))),
            else_=None,
        )
    raise RuntimeError(f"Unsupported database dialect for posting-date ordering: {dialect_name}")


@router.get("/normalized", response_model=NormalizedJobsResponse)
def list_normalized_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    title: str | None = None,
    company: str | None = None,
    location: str | None = None,
    source: str | None = None,
):
    filters = [Job.status == "completed"]
    for value, column in (
        (title, Job.title),
        (company, Job.company),
        (location, Job.location),
    ):
        if value and value.strip():
            filters.append(column.ilike(contains_pattern(value), escape="\\"))

    total = db.scalar(select(func.count(Job.id)).where(*filters)) or 0
    posting_date_order = _posting_date_order_expression(db)
    start = (page - 1) * limit
    rows = list(
        db.execute(
            select(Job.id, Job.title, Job.company, Job.location, Job.posting_date, Job.source)
            .where(*filters)
            .order_by(posting_date_order.desc().nulls_last(), Job.id.asc())
            .offset(start)
            .limit(limit)
        ).all()
    )
    items = [
        NormalizedJobHeader(
            id=row.id,
            title=row.title,
            company=row.company,
            location=row.location,
            posting_date=row.posting_date,
            source=row.source,
        )
        for row in rows
    ]
    return NormalizedJobsResponse(items=items, total=total, page=page, limit=limit)


@router.get("/interests", response_model=InterestsPage)
def list_my_interests(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    title: str | None = None,
    company: str | None = None,
    location: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows, total = list_interests(
        db, current_user.id, title=title, company=company, location=location, page=page, limit=limit
    )
    items = [
        InterestItem(
            id=interest.id,
            job_id=interest.job_id,
            created_at=interest.created_at,
            job=InterestJobHeader(
                id=job.id,
                title=job.title,
                company=job.company,
                location=job.location,
                url=job.url,
                source=job.source,
                posting_date=job.posting_date,
            ),
        )
        for interest, job in rows
    ]
    return InterestsPage(items=items, total=total, page=page, limit=limit, total_pages=-(-total // limit))


@router.get("/{job_id}")
def get_job(job_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    interested = db.query(JobInterest).filter_by(user_id=current_user.id, job_id=job_id).first() is not None
    is_tracked = db.query(ApplicationJournal).filter_by(user_id=current_user.id, job_id=job_id).first() is not None
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "id": job.id,
        "url": job.url,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "salary": job.salary,
        "source": job.source,
        "posting_date": job.posting_date,
        "summary": job.summary,
        "key_responsibilities": job.key_responsibilities,
        "requirements": job.required,
        "desirables": job.desirable,
        "tools_and_technologies": job.tools_and_technologies,
        "additionals": job.additionals,
        "status": job.status,
        "submitter_id": job.submitter_id,
        "created_at": job.created_at,
        "has_write_access": job.submitter_id == current_user.id or current_user.role == "admin",
        "is_interested": interested,
        "is_tracked": is_tracked
    }


@router.post("/{job_id}/interest", status_code=201)
def interest(job_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != "completed":
        raise HTTPException(409, "Job normalization is not completed")
    try:
        item, created = ensure_interest(db, current_user.id, job_id)
        db.commit()
    except IntegrityError:
        db.rollback()
        item, created = ensure_interest(db, current_user.id, job_id)
    return {"id": item.id, "status": "created" if created else "existing"}


@router.delete("/{job_id}/interest", status_code=204)
def remove_job_interest(job_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not remove_interest(db, current_user.id, job_id):
        raise HTTPException(404, "Interest not found")
    db.commit()


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.submitter_id != current_user.id and current_user.role != "admin":
        raise HTTPException(403, "Forbidden")
    db.execute(delete(JobInterest).where(JobInterest.job_id == job_id))
    db.delete(job)
    db.commit()
