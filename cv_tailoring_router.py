import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from auth import get_current_user
from database import SessionLocal, get_db
from models import CVRequest, Job, JobMatchingResult, ProcessingJob, ProcessingJobStatus, ProcessingJobType, TailoredCVRecord, User, UserProfile
from pipeline.cv_tailoring import build_tailored_cv
from pipeline.llm_matching import JobData
from pipeline.markdown_writer import render_tailored_cv_markdown, suggest_filename
from schemas import CvTailoringRequest, ProcessingJobOut
from serialization import dict_to_user_profile
from storage import build_blob_path, generate_temporary_download_url, upload_markdown
from cv_service import validate_cv_selection

router = APIRouter(tags=["cv-tailoring"])
logger = logging.getLogger("tip-api")


def _run_cv_tailoring(proc_job_id: str, user_id: str, matching_ids: list[str], mode: str, output_language: str, request_id: str) -> None:
    db = SessionLocal()
    proc_job = None
    try:
        proc_job = db.get(ProcessingJob, proc_job_id)
        if proc_job is None:
            return
        proc_job.status = ProcessingJobStatus.RUNNING
        db.commit()

        matchings = [db.get(JobMatchingResult, matching_id) for matching_id in matching_ids]
        if any(matching is None or matching.user_id != user_id for matching in matchings):
            raise ValueError("Matching result not found")
        validate_cv_selection([{"user_id": matching.user_id} for matching in matchings], mode)
        first_matching = matchings[0]
        profile_row = db.get(UserProfile, first_matching.profile_id)
        if profile_row is None:
            raise ValueError("Matching context not found")
        profile = dict_to_user_profile(profile_row.data)
        selected = matchings if mode == "per_job" else matchings[:1]
        records = []
        for matching in selected:
            job = db.get(Job, matching.job_id)
            if job is None:
                raise ValueError("Matching context not found")
            title = job.title
            if mode == "group_all":
                titles = [db.get(Job, item.job_id).title for item in matchings if db.get(Job, item.job_id)]
                title = " / ".join(titles)
            job_data = JobData(
                title=title,
                required=job.required,
                desirable=job.desirable,
                technical_stack=job.technical_stack,
                key_responsibilities=job.key_responsibilities,
                summary=job.summary,
            )
            tailored = build_tailored_cv(profile, job_data, match_score=matching.score, output_language=output_language)
            record = TailoredCVRecord(
                matching_id=matching.id,
                request_id=request_id,
                user_id=user_id,
                blob_path="",
                mode=mode,
                status="completed",
                target_job_ids=[item.job_id for item in matchings],
            )
            db.add(record)
            db.flush()
            blob_path = build_blob_path(user_id, record.id, suggest_filename(tailored))
            upload_markdown(blob_path, render_tailored_cv_markdown(tailored))
            record.blob_path = blob_path
            records.append(record)
        db.commit()

        proc_job.status = ProcessingJobStatus.DONE
        proc_job.result_id = records[0].id
        request = db.get(CVRequest, request_id)
        if request:
            request.status = "completed"
        db.commit()
    except Exception as e:  # noqa: BLE001 — surface via polled status
        logger.exception("CV tailoring failed", extra={"processing_job_id": proc_job_id})
        if proc_job is not None:
            proc_job.status = ProcessingJobStatus.FAILED
            proc_job.error = "CV generation failed"
            request = db.get(CVRequest, request_id)
            if request:
                request.status = "failed"
                request.error = "CV generation failed"
            db.commit()
    finally:
        db.close()


@router.post("/cv/tailor", status_code=202, response_model=ProcessingJobOut)
@router.post("/cv-tailoring/tailor", status_code=202, response_model=ProcessingJobOut)
def tailor_cv(
    payload: CvTailoringRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    matchings = [db.get(JobMatchingResult, matching_id) for matching_id in payload.matching_ids]
    if any(matching is None or matching.user_id != current_user.id for matching in matchings):
        raise HTTPException(404, "Matching result not found")

    proc_job = ProcessingJob(user_id=current_user.id, job_type=ProcessingJobType.CV_TAILOR)
    cv_request = CVRequest(user_id=current_user.id, matching_ids=payload.matching_ids, mode=payload.mode, status="processing")
    db.add(cv_request)
    db.add(proc_job)
    db.commit()

    background_tasks.add_task(
        _run_cv_tailoring, proc_job.id, current_user.id, payload.matching_ids, payload.mode, payload.output_language, cv_request.id
    )

    return ProcessingJobOut(id=proc_job.id, status=proc_job.status.value, result_id=proc_job.result_id)


@router.get("/cv")
def list_cvs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cvs = db.execute(
        select(TailoredCVRecord).where(TailoredCVRecord.user_id == current_user.id).order_by(desc(TailoredCVRecord.created_at))
    ).scalars().all()
    return [
        {
            "id": item.id,
            "request_id": item.request_id,
            "matching_id": item.matching_id,
            "blob_path": item.blob_path,
            "mode": item.mode,
            "status": item.status,
            "target_job_ids": item.target_job_ids,
            "download_url": generate_temporary_download_url(item.blob_path),
        }
        for item in cvs
    ]


@router.get("/cv/{tailored_cv_id}")
def get_cv(tailored_cv_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.get(TailoredCVRecord, tailored_cv_id)
    if not record or record.user_id != current_user.id:
        raise HTTPException(404, "Tailored CV not found")
    return {
        "id": record.id,
        "request_id": record.request_id,
        "matching_id": record.matching_id,
        "blob_path": record.blob_path,
        "mode": record.mode,
        "status": record.status,
        "target_job_ids": record.target_job_ids,
        "download_url": generate_temporary_download_url(record.blob_path),
    }


@router.delete("/cv/{tailored_cv_id}", status_code=204)
def delete_cv(tailored_cv_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.get(TailoredCVRecord, tailored_cv_id)
    if not record or record.user_id != current_user.id:
        raise HTTPException(404, "Tailored CV not found")
    db.delete(record)
    db.commit()
