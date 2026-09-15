import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from auth.security import get_current_user
from shared.database import SessionLocal, get_db
from matching.matching_service import create_pending_match_report, process_match_report
from shared.models import JobMatchingResult, MatchReport, ProcessingJob, ProcessingJobStatus, ProcessingJobType, User
from shared.schemas import JobMatchingRequest, ProcessingJobOut

router = APIRouter(prefix="/matching", tags=["matching"])
logger = logging.getLogger("tip-api")


class MatchCreateRequest(BaseModel):
    job_ids: list[str]


async def _run_match_report(processing_job_id: str, report_id: str, user_id: str, job_ids: list[str]) -> None:
    db = SessionLocal()
    processing_job = None
    try:
        processing_job = db.get(ProcessingJob, processing_job_id)
        if processing_job is None:
            return
        processing_job.status = ProcessingJobStatus.RUNNING
        db.commit()
        await process_match_report(db, report_id, user_id, job_ids)
        processing_job.status = ProcessingJobStatus.DONE
        processing_job.result_id = report_id
        db.commit()
    except Exception as exc:  # noqa: BLE001 - surface via polled status
        logger.exception("Matching failed", extra={"processing_job_id": processing_job_id})
        db.rollback()
        processing_job = db.get(ProcessingJob, processing_job_id)
        report = db.get(MatchReport, report_id)
        if processing_job is not None:
            processing_job.status = ProcessingJobStatus.FAILED
            processing_job.error = "Matching failed"
        if report is not None:
            report.status = "failed"
        db.commit()
    finally:
        db.close()


@router.post("", status_code=202, response_model=ProcessingJobOut)
def create_match_report(
    payload: MatchCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.job_ids:
        raise HTTPException(400, "At least one job id is required")

    try:
        report = create_pending_match_report(db, current_user.id, payload.job_ids)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    processing_job = ProcessingJob(user_id=current_user.id, job_type=ProcessingJobType.MATCHING)
    db.add(processing_job)
    db.commit()
    db.refresh(processing_job)
    background_tasks.add_task(_run_match_report, processing_job.id, report.id, current_user.id, payload.job_ids)
    return ProcessingJobOut(id=processing_job.id, status=processing_job.status.value, result_id=report.id)


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


@router.post("/match", status_code=202, response_model=ProcessingJobOut)
def match_job(
    payload: JobMatchingRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    request = MatchCreateRequest(job_ids=[payload.job_id])
    return create_match_report(request, background_tasks, current_user, db)
