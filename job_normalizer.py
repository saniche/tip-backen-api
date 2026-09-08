from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from llm_structured import call_openai_structured
from models import Job
from schemas import JobExtraction

router = APIRouter(prefix="/job-normalizer", tags=["job-normalizer"])

SYSTEM_PROMPT = (
    "You extract structured job posting data from raw text (which may contain one or more distinct "
    "postings, e.g. a scraped search-results page). Extract every distinct posting found. Never invent "
    "details not present in the text — use null for missing optional fields and an empty array for "
    "missing lists."
)


class JobNormalizeRequest(BaseModel):
    raw_text: str


@router.post("/extract", response_model=JobExtraction)
async def extract_jobs(payload: JobNormalizeRequest, db: Session = Depends(get_db)):
    extraction = await call_openai_structured(SYSTEM_PROMPT, payload.raw_text, JobExtraction)

    for job in extraction.jobs:
        # Jobs are global/deduplicated by url, not scoped by user — skip re-saving an already-known posting.
        if job.url:
            existing = db.execute(select(Job).where(Job.url == job.url)).scalar_one_or_none()
            if existing:
                continue

        db.add(
            Job(
                url=job.url,
                title=job.title,
                company=job.company,
                location=job.location,
                salary=job.salary,
                source=job.source,
                summary=job.summary,
                posting_date=job.posting_date,
                key_responsibilities=job.key_responsibilities,
                required=job.required.model_dump(),
                desirable=job.desirable.model_dump(),
                technical_stack=job.technical_stack,
            )
        )
    db.commit()

    return extraction
