from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from llm_structured import StructuredProviderError
from matching_service import create_match_report as persist_match_report
from models import JobMatchingResult, MatchReport, User
from schemas import JobMatchingOut, JobMatchingRequest

router = APIRouter(prefix="/matching", tags=["matching"])


class MatchCreateRequest(BaseModel):
    job_ids: list[str]


@router.post("", status_code=202)
async def create_match_report(
    payload: MatchCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.job_ids:
        raise HTTPException(400, "At least one job id is required")

    try:
        report = await persist_match_report(db, current_user.id, payload.job_ids)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except StructuredProviderError as exc:
        raise HTTPException(502, "External processing failed. Please try again later.") from exc
    return {"report_id": report.id, "status": "completed"}


@router.get("/reports")
def list_match_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reports = (
        db.execute(
            select(MatchReport).where(MatchReport.user_id == current_user.id).order_by(desc(MatchReport.created_at))
        )
        .scalars()
        .all()
    )
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

    results = (
        db.execute(
            select(JobMatchingResult)
            .where(JobMatchingResult.report_id == report.id)
            .order_by(desc(JobMatchingResult.score))
        )
        .scalars()
        .all()
    )
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
async def match_job(
    payload: JobMatchingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    request = MatchCreateRequest(job_ids=[payload.job_id])
    response = await create_match_report(request, current_user, db)
    report_id = response["report_id"]
    result = (
        db.execute(
            select(JobMatchingResult)
            .where(JobMatchingResult.report_id == report_id)
            .order_by(desc(JobMatchingResult.score))
        )
        .scalars()
        .first()
    )
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
