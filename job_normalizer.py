from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Job, JobInterest, User

router = APIRouter(prefix="/jobs", tags=["jobs"])

SYSTEM_PROMPT = (
    "You extract structured job posting data from raw text (which may contain one or more distinct "
    "postings, e.g. a scraped search-results page). Extract every distinct posting found. Never invent "
    "details not present in the text — use null for missing optional fields and an empty array for "
    "missing lists."
)


class JobNormalizeRequest(BaseModel):
    url: str
    content: str
    title: str | None = None
    company: str | None = None
    location: str | None = None


@router.post("/normalize", status_code=201)
def normalize_job(payload: JobNormalizeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.execute(select(Job).where(Job.url == payload.url)).scalar_one_or_none()
    if existing:
        return {"id": existing.id, "status": "existing"}
    job = Job(url=payload.url, title=payload.title or payload.content.splitlines()[0][:200], company=payload.company, location=payload.location, summary=payload.content, submitter_id=current_user.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"id": job.id, "status": "created", "title": job.title, "url": job.url, "created_at": job.created_at}


@router.get("")
def list_jobs(title: str | None = None, company: str | None = None, location: str | None = None, limit: int = Query(50, le=100), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(Job).order_by(desc(Job.created_at)).limit(limit)
    if title: query = query.where(Job.title.ilike(f"%{title}%"))
    if company: query = query.where(Job.company.ilike(f"%{company}%"))
    if location: query = query.where(Job.location.ilike(f"%{location}%"))
    return [{"id": job.id, "url": job.url, "title": job.title, "company": job.company, "location": job.location, "created_at": job.created_at} for job in db.execute(query).scalars()]


@router.get("/{job_id}")
def get_job(job_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job: raise HTTPException(404, "Job not found")
    return {"id": job.id, "url": job.url, "title": job.title, "company": job.company, "location": job.location, "summary": job.summary}


@router.post("/{job_id}/interest", status_code=201)
def interest(job_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.get(Job, job_id): raise HTTPException(404, "Job not found")
    existing = db.execute(select(JobInterest).where(JobInterest.user_id == current_user.id, JobInterest.job_id == job_id)).scalar_one_or_none()
    if existing: return {"id": existing.id, "status": "existing"}
    item = JobInterest(user_id=current_user.id, job_id=job_id); db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id, "status": "created"}


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job: raise HTTPException(404, "Job not found")
    if job.submitter_id != current_user.id and current_user.role != "admin": raise HTTPException(403, "Forbidden")
    db.delete(job); db.commit()
