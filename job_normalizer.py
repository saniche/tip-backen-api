import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from auth import get_current_user
from database import SessionLocal, get_db
from job_service import normalize_job_content
from models import Job, JobInterest, ProcessingJob, ProcessingJobStatus, ProcessingJobType, User
from schemas import JobNormalizeOut, JobNormalizeRequest

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger("tip-api")

SYSTEM_PROMPT = (
    "You extract structured job posting data from raw text (which may contain one or more distinct "
    "postings, e.g. a scraped search-results page). Extract every distinct posting found. Never invent "
    "details not present in the text — use null for missing optional fields and an empty array for "
    "missing lists."
)


async def _run_job_normalization(processing_job_id: str, job_id: str) -> None:
    db = SessionLocal()
    try:
        processing_job = db.get(ProcessingJob, processing_job_id)
        job = db.get(Job, job_id)
        if processing_job is None or job is None:
            return
        processing_job.status = ProcessingJobStatus.RUNNING
        job.status = "processing"
        db.commit()
        structured = await normalize_job_content(job.summary or "")
        for key, value in structured.items():
            setattr(job, key, value)
        job.status = "completed"
        processing_job.status = ProcessingJobStatus.DONE
        processing_job.result_id = job.id
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
        return {"id": existing.id, "status": "existing"}
    job = Job(
        url=payload.url,
        title=payload.title or payload.content.splitlines()[0][:200],
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
    background_tasks.add_task(_run_job_normalization, processing_job.id, job.id)
    return {
        "id": job.id,
        "status": "processing",
        "processing_job_id": processing_job.id,
        "title": job.title,
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


@router.get("/{job_id}")
def get_job(job_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "id": job.id,
        "url": job.url,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "summary": job.summary,
        "key_responsibilities": job.key_responsibilities,
        "required": job.required,
        "desirable": job.desirable,
        "technical_stack": job.technical_stack,
        "status": job.status,
    }


@router.post("/{job_id}/interest", status_code=201)
def interest(job_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.get(Job, job_id):
        raise HTTPException(404, "Job not found")
    existing = db.execute(
        select(JobInterest).where(JobInterest.user_id == current_user.id, JobInterest.job_id == job_id)
    ).scalar_one_or_none()
    if existing:
        return {"id": existing.id, "status": "existing"}
    item = JobInterest(user_id=current_user.id, job_id=job_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "status": "created"}


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.submitter_id != current_user.id and current_user.role != "admin":
        raise HTTPException(403, "Forbidden")
    db.delete(job)
    db.commit()
