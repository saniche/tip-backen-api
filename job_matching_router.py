from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Job, JobMatchingResult, MatchReport, User, UserProfile
from pipeline.job_matching import build_match_result
from pipeline.llm_matching import JobData, get_llm_match_output
from schemas import JobMatchingOut, JobMatchingRequest

router = APIRouter(prefix="/matching", tags=["matching"])


class MatchCreateRequest(BaseModel):
    job_ids: list[str]


@router.post("", status_code=202)
def create_match_report(
    payload: MatchCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.job_ids:
        raise HTTPException(400, "At least one job id is required")

    profile_row = (
        db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id).order_by(desc(UserProfile.created_at)))
        .scalars()
        .first()
    )
    if not profile_row:
        raise HTTPException(400, "No profile found — run ProfileBuilder first")

    report = MatchReport(user_id=current_user.id, profile_id=profile_row.id)
    db.add(report)
    db.flush()

    created_results = []
    for job_id in payload.job_ids:
        job = db.get(Job, job_id)
        if not job:
            continue

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
            report_id=report.id,
            user_id=current_user.id,
            job_id=job.id,
            profile_id=profile_row.id,
            score=result.score,
            eligible=result.eligible,
            scoring_status=result.scoring_status,
            breakdown=result.breakdown,
            llm_match_output=asdict(llm_output),
            profile_snapshot=dict(profile_row.data),
            job_snapshot={
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "required": job.required,
                "desirable": job.desirable,
                "technical_stack": job.technical_stack,
            },
            rules_version="v1",
        )
        db.add(db_matching)
        created_results.append(db_matching)

    for rank, result in enumerate(sorted(created_results, key=lambda item: item.score or 0, reverse=True), start=1):
        result.rank = rank

    db.commit()
    return {"report_id": report.id, "status": report.status}


@router.get("/reports")
def list_match_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reports = db.execute(select(MatchReport).where(MatchReport.user_id == current_user.id).order_by(desc(MatchReport.created_at))).scalars().all()
    return [
        {
            "id": report.id,
            "status": report.status,
            "created_at": report.created_at.isoformat(),
            "profile_id": report.profile_id,
        }
        for report in reports
    ]


@router.get("/reports/{report_id}")
def get_match_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.get(MatchReport, report_id)
    if not report or report.user_id != current_user.id:
        raise HTTPException(404, "Match report not found")

    results = db.execute(
        select(JobMatchingResult).where(JobMatchingResult.report_id == report.id).order_by(desc(JobMatchingResult.score))
    ).scalars().all()
    return {
        "id": report.id,
        "status": report.status,
        "results": [
            {
                "id": result.id,
                "job_id": result.job_id,
                "score": result.score,
                "eligible": result.eligible,
                "scoring_status": result.scoring_status,
                "breakdown": result.breakdown,
                "rank": result.rank,
                "explanation": result.llm_match_output,
            }
            for result in results
        ],
    }


@router.delete("/reports/{report_id}", status_code=204)
def delete_match_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.get(MatchReport, report_id)
    if not report or report.user_id != current_user.id:
        raise HTTPException(404, "Match report not found")
    db.execute(select(JobMatchingResult).where(JobMatchingResult.report_id == report.id))
    for result in db.execute(select(JobMatchingResult).where(JobMatchingResult.report_id == report.id)).scalars().all():
        db.delete(result)
    db.delete(report)
    db.commit()


@router.post("/match", response_model=JobMatchingOut)
def match_job(
    payload: JobMatchingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    request = MatchCreateRequest(job_ids=[payload.job_id])
    response = create_match_report(request, current_user, db)
    report_id = response["report_id"]
    result = db.execute(select(JobMatchingResult).where(JobMatchingResult.report_id == report_id).order_by(desc(JobMatchingResult.score))).scalars().first()
    if result is None:
        raise HTTPException(404, "Matching result not found")
    return JobMatchingOut(
        id=result.id,
        job_id=result.job_id,
        score=int(result.score),
        eligible=result.eligible,
        scoring_status=result.scoring_status,
        breakdown=result.breakdown,
    )
