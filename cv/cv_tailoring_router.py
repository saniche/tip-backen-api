import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

import shared.queue as background_queue
from api.openapi import error_responses
from api.schemas.requests.tailoring import CvTailoringRequest
from api.schemas.responses.processing import ProcessingJobResponse
from api.schemas.responses.tailoring import CvMetadataResponse
from auth.security import get_current_user
from candidate_profile.serialization import dict_to_user_profile
from cv.cv_service import delete_tailored_record, validate_cv_selection
from cv.cv_tailoring import EmptyExperienceError, build_tailored_cv
from cv.job_group import merge_jobs
from cv.markdown_writer import render_tailored_cv_markdown, suggest_filename
from shared.database import SessionLocal, get_db
from shared.models import (
    CVRequest,
    Job,
    JobMatchingResult,
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    TailoredCVRecord,
    User,
    UserProfile,
)
from shared.processing_artifacts import artifact_id, prepare_filenames
from shared.retry import is_transient_failure
from shared.storage import build_blob_path, delete_blob, generate_temporary_download_url, upload_markdown

router = APIRouter()
logger = logging.getLogger("tip-api")


async def _run_cv_tailoring(
    proc_job_id: str, user_id: str, matching_ids: list[str], mode: str, output_language: str, request_id: str,
    *, db: Session | None = None, retry_transient: bool = False,
) -> None:
    db = db if db is not None else SessionLocal()
    proc_job = None
    uploaded_blob_paths = []
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
        generated = []
        for matching in selected:
            if mode == "per_job":
                job = db.get(Job, matching.job_id)
                if job is None:
                    raise ValueError("Matching context not found")
                job_data = merge_jobs([job]).data
                score = matching.score
            else:
                group_jobs = [db.get(Job, item.job_id) for item in matchings]
                if any(job is None for job in group_jobs):
                    raise ValueError("Matching context not found")
                job_data = merge_jobs(group_jobs).data
                scores = [item.score for item in matchings]
                score = round(sum(scores) / len(scores)) if all(v is not None for v in scores) else None
            tailored = await build_tailored_cv(profile, job_data, match_score=score, output_language=output_language)
            generated.append((matching, tailored))
        filenames = prepare_filenames(
            db, proc_job_id, [suggest_filename(tailored, profile) for _, tailored in generated]
        )
        records = []
        for index, ((matching, tailored), filename) in enumerate(zip(generated, filenames, strict=True)):
            record = TailoredCVRecord(
                id=artifact_id(proc_job_id, index),
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
            blob_path = build_blob_path(user_id, record.id, filename)
            uploaded_blob_paths.append(blob_path)
            upload_markdown(blob_path, render_tailored_cv_markdown(tailored, profile))
            record.blob_path = blob_path
            records.append(record)
        proc_job.status = ProcessingJobStatus.DONE
        proc_job.result_id = records[0].id
        request = db.get(CVRequest, request_id)
        if request:
            request.status = "completed"
        db.commit()
    except Exception as failure:  # noqa: BLE001 — surface via polled status
        logger.exception("CV tailoring failed", extra={"processing_job_id": proc_job_id})
        db.rollback()
        for blob_path in uploaded_blob_paths:
            try:
                delete_blob(blob_path)
            except Exception:  # noqa: BLE001 - original processing failure remains authoritative
                logger.warning("CV blob cleanup failed", extra={"processing_job_id": proc_job_id})
        if retry_transient and is_transient_failure(failure):
            raise
        message = (
            f"CV validation failed: {failure}" if isinstance(failure, EmptyExperienceError) else "CV generation failed"
        )
        proc_job = db.get(ProcessingJob, proc_job_id)
        if proc_job is not None:
            proc_job.status = ProcessingJobStatus.FAILED
            proc_job.error = message
            request = db.get(CVRequest, request_id)
            if request:
                request.status = "failed"
                request.error = message
            db.commit()
    finally:
        db.close()


@router.post(
    "/cv/tailor",
    status_code=202,
    response_model=ProcessingJobResponse,
    summary="Start CV tailoring",
    description="Queues a tailored CV for the supplied matching results and returns a processing-job identifier.",
    tags=["CV Tailoring"],
    responses=error_responses(401, 404, 422, 500, 502, 503),
)
async def tailor_cv(
    payload: CvTailoringRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    matchings = [db.get(JobMatchingResult, matching_id) for matching_id in payload.matching_ids]
    if any(matching is None or matching.user_id != current_user.id for matching in matchings):
        raise HTTPException(404, "Matching result not found")

    queue = await background_queue.connect_queue()
    proc_job = ProcessingJob(user_id=current_user.id, job_type=ProcessingJobType.CV_TAILOR)
    cv_request = CVRequest(
        user_id=current_user.id, matching_ids=payload.matching_ids, mode=payload.mode, status="processing"
    )
    db.add(cv_request)
    try:
        db.flush()
        outbox = background_queue.persist_work(db, proc_job, "cv_tailoring", {
            "user_id": current_user.id,
            "matching_ids": payload.matching_ids,
            "mode": payload.mode,
            "output_language": payload.output_language,
            "request_id": cv_request.id,
        })
        response = ProcessingJobResponse(id=proc_job.id, status=proc_job.status, result_id=proc_job.result_id)
        await background_queue.publish_work(queue, db, outbox)
    finally:
        await queue.aclose()

    return response


@router.get(
    "/cv",
    response_model=list[CvMetadataResponse],
    status_code=200,
    summary="List tailored CVs",
    description="Lists completed tailored CVs owned by the authenticated user.",
    tags=["CV Tailoring"],
    responses=error_responses(401, 500, 503),
)
def list_cvs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cvs = (
        db.execute(
            select(TailoredCVRecord)
            .where(
                TailoredCVRecord.user_id == current_user.id,
                TailoredCVRecord.kind == "cv",
                TailoredCVRecord.status == "completed",
            )
            .order_by(desc(TailoredCVRecord.created_at))
        )
        .scalars()
        .all()
    )
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


@router.get(
    "/cv/{tailored_cv_id}",
    response_model=CvMetadataResponse,
    status_code=200,
    summary="Get a tailored CV",
    description="Returns metadata and a temporary download URL for an owned completed CV.",
    tags=["CV Tailoring"],
    responses=error_responses(401, 404, 500, 503),
)
def get_cv(tailored_cv_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.get(TailoredCVRecord, tailored_cv_id)
    if not record or record.user_id != current_user.id or record.kind != "cv":
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


@router.delete(
    "/cv/{tailored_cv_id}",
    status_code=204,
    summary="Delete a tailored CV",
    description="Deletes an owned tailored CV and its stored document.",
    tags=["CV Tailoring"],
    responses=error_responses(401, 404, 500, 503),
)
def delete_cv(tailored_cv_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.get(TailoredCVRecord, tailored_cv_id)
    if not record or record.user_id != current_user.id:
        raise HTTPException(404, "Tailored CV not found")
    delete_tailored_record(db, record, delete_blob)
