from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Job, JobMatchingResult, User, UserProfile
from pipeline.job_matching import build_match_result
from pipeline.llm_matching import JobData, get_llm_match_output
from schemas import JobMatchingOut, JobMatchingRequest

router = APIRouter(prefix="/job-matching", tags=["job-matching"])


@router.post("/match", response_model=JobMatchingOut)
def match_job(
    payload: JobMatchingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.get(Job, payload.job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    # Most recent profile row for this user — UserProfile is append-only, so this is the "current" version.
    profile_row = (
        db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id).order_by(desc(UserProfile.created_at)))
        .scalars()
        .first()
    )
    if not profile_row:
        raise HTTPException(400, "No profile found — run ProfileBuilder first")

    job_data = JobData(
        title=job.title,
        required=job.required,
        desirable=job.desirable,
        technical_stack=job.technical_stack,
        key_responsibilities=job.key_responsibilities,
        company=job.company,
        location=job.location,
        salary=job.salary,
        url=job.url,
        source=job.source,
        summary=job.summary,
    )

    llm_output = get_llm_match_output(profile_row.data, job_data)
    result = build_match_result(llm_output)

    db_matching = JobMatchingResult(
        user_id=current_user.id,
        job_id=job.id,
        profile_id=profile_row.id,  # locks this match to the exact profile version used
        score=result.score,
        eligible=result.eligible,
        scoring_status=result.scoring_status,
        breakdown=result.breakdown,
        llm_match_output=asdict(llm_output),
    )
    db.add(db_matching)
    db.commit()

    return JobMatchingOut(
        id=db_matching.id,
        job_id=job.id,
        score=result.score,
        eligible=result.eligible,
        scoring_status=result.scoring_status,
        breakdown=result.breakdown,
    )
