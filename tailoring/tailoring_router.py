import asyncio
import logging
from profile.profile_service import resolve_profile
from profile.serialization import dict_to_user_profile

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from auth.security import get_current_user
from cover_letter.cover_letter_tailoring import CoverLetterGroundingError
from cv.cv_service import delete_tailored_record
from cv.cv_tailoring import GroundingError
from defaults.defaults_service import KIND_COVER_LETTER, KIND_CV, get_default_document
from shared.database import SessionLocal, get_db
from shared.llm_structured import StructuredProviderError
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
from shared.processing_service import complete_processing_job, fail_processing_job
from shared.schemas import ProcessingJobOut, TailoringRequestIn
from shared.storage import build_blob_path, delete_blob, generate_temporary_download_url, upload_markdown
from tailoring.tailoring_service import generate_document, plan_work_items

router = APIRouter(tags=["tailoring"])
logger = logging.getLogger("tip-api")

MAX_PARALLEL_LLM_CALLS = 3
_KIND_LABEL = {"cv": "CV", "cover_letter": "cover letter"}


def _item_error(kind: str, exc: Exception) -> str:
    label = _KIND_LABEL.get(kind, "document")
    if isinstance(exc, GroundingError):
        return f"The generated {label} failed validation: {exc}"
    if isinstance(exc, CoverLetterGroundingError):
        return f"The generated {label} contained content not supported by the profile and job"
    if isinstance(exc, StructuredProviderError):
        return f"The AI provider could not produce the {label}; try again"
    return f"The {label} could not be generated"


def _latest_scores(db: Session, user_id: str, profile_id: str, job_ids: list[str]) -> dict[str, int | None]:
    """Most recent match score per job for this user and profile, if the job was ever matched."""
    rows = db.execute(
        select(JobMatchingResult.job_id, JobMatchingResult.score)
        .where(
            JobMatchingResult.user_id == user_id,
            JobMatchingResult.profile_id == profile_id,
            JobMatchingResult.job_id.in_(job_ids),
        )
        .order_by(JobMatchingResult.created_at)
    ).all()
    return {job_id: (round(score) if score is not None else None) for job_id, score in rows}


async def _run_tailoring(proc_job_id: str, request_id: str) -> None:
    db = SessionLocal()
    uploaded_blob_paths: list[str] = []
    committed = False
    try:
        proc_job = db.get(ProcessingJob, proc_job_id)
        request = db.get(CVRequest, request_id)
        if proc_job is None or request is None:
            return
        proc_job.status = ProcessingJobStatus.RUNNING
        db.commit()

        user_id = request.user_id
        profile_row = db.get(UserProfile, request.profile_id)
        if profile_row is None:
            raise ValueError("Profile not found")
        profile = dict_to_user_profile(profile_row.data)
        jobs_by_id = {job.id: job for job in db.execute(select(Job).where(Job.id.in_(request.job_ids))).scalars()}
        jobs = [jobs_by_id[job_id] for job_id in request.job_ids]

        style = {}
        for kind in (KIND_CV, KIND_COVER_LETTER):
            document = get_default_document(db, user_id, kind)
            style[kind] = document.content if document else None
        scores = _latest_scores(db, user_id, profile_row.id, request.job_ids)
        language = request.output_language
        items = plan_work_items(jobs, request.mode, request.cover_letter_enabled, request.cover_letter_mode)

        semaphore = asyncio.Semaphore(MAX_PARALLEL_LLM_CALLS)

        async def run(item):
            score = scores.get(item.jobs[0].id) if item.kind == KIND_CV and item.scope == "per_job" else None
            async with semaphore:
                try:
                    return await generate_document(item, profile, language, style[item.kind], score)
                except Exception as exc:  # noqa: BLE001 - recorded per document, the others carry on
                    logger.warning("Tailoring item failed", extra={"kind": item.kind, "error": type(exc).__name__})
                    return exc

        results = await asyncio.gather(*(run(item) for item in items))

        completed = failed = 0
        first_error = None
        for item, result in zip(items, results, strict=True):
            record = TailoredCVRecord(
                request_id=request.id,
                user_id=user_id,
                matching_id=None,
                blob_path="",
                mode=item.scope,
                kind=item.kind,
                job_id=item.jobs[0].id if item.scope == "per_job" else None,
                profile_id=profile_row.id,
                target_job_ids=[job.id for job in item.jobs],
            )
            db.add(record)
            if isinstance(result, Exception):
                record.status, record.error = "failed", _item_error(item.kind, result)
                failed, first_error = failed + 1, first_error or record.error
                continue
            db.flush()
            blob_path = build_blob_path(user_id, record.id, result.filename)
            try:
                upload_markdown(blob_path, result.content)
            except Exception:  # noqa: BLE001
                logger.exception("Tailored document upload failed")
                record.status, record.error = "failed", "The document could not be stored"
                failed, first_error = failed + 1, first_error or record.error
                continue
            uploaded_blob_paths.append(blob_path)
            record.blob_path, record.warning = blob_path, result.warning
            completed += 1

        request.status = "completed" if failed == 0 else ("partial" if completed else "failed")
        request.error = None if completed else first_error
        db.commit()
        committed = True
        if completed:
            complete_processing_job(db, proc_job_id, request_id)
        else:
            fail_processing_job(db, proc_job_id, first_error or "Tailoring failed")
    except Exception:  # noqa: BLE001 - surfaced through the polled processing job
        logger.exception("Tailoring failed", extra={"processing_job_id": proc_job_id})
        db.rollback()
        if not committed:
            for blob_path in uploaded_blob_paths:
                try:
                    delete_blob(blob_path)
                except Exception:  # noqa: BLE001
                    logger.warning("Tailoring blob cleanup failed", extra={"processing_job_id": proc_job_id})
            request = db.get(CVRequest, request_id)
            if request is not None:
                request.status, request.error = "failed", "Tailoring failed"
            db.commit()
            fail_processing_job(db, proc_job_id, "Tailoring failed")
    finally:
        db.close()


def _document_out(record: TailoredCVRecord) -> dict:
    available = record.status == "completed" and bool(record.blob_path)
    return {
        "id": record.id,
        "kind": record.kind,
        "scope": record.mode,
        "job_id": record.job_id,
        "job_ids": record.target_job_ids,
        "status": record.status,
        "error": record.error,
        "warning": record.warning,
        "filename": record.blob_path.rsplit("/", 1)[-1] if available else None,
        "download_url": generate_temporary_download_url(record.blob_path) if available else None,
        "created_at": record.created_at,
    }


def _request_out(request: CVRequest, documents: list[TailoredCVRecord] | None = None) -> dict:
    payload = {
        "id": request.id,
        "status": request.status,
        "error": request.error,
        "job_ids": request.job_ids,
        "profile_id": request.profile_id,
        "cv_mode": request.mode,
        "cover_letter": {"enabled": request.cover_letter_enabled, "mode": request.cover_letter_mode},
        "output_language": request.output_language,
        "created_at": request.created_at,
    }
    if documents is not None:
        payload["documents"] = [_document_out(item) for item in documents]
    return payload


def _owned_request(db: Session, user_id: str, request_id: str) -> CVRequest:
    request = db.get(CVRequest, request_id)
    if request is None or request.user_id != user_id or not request.job_ids:
        raise HTTPException(404, "Tailoring request not found")
    return request


def _request_documents(db: Session, request_id: str) -> list[TailoredCVRecord]:
    return list(
        db.execute(
            select(TailoredCVRecord)
            .where(TailoredCVRecord.request_id == request_id)
            .order_by(TailoredCVRecord.kind, TailoredCVRecord.created_at)
        )
        .scalars()
        .all()
    )


@router.post("/tailoring", status_code=202, response_model=ProcessingJobOut)
def create_tailoring_request(
    payload: TailoringRequestIn,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        profile = resolve_profile(db, current_user.id, payload.profile_id)
    except ValueError as exc:
        raise HTTPException(404, "Profile not found") from exc
    jobs = {job.id: job for job in db.execute(select(Job).where(Job.id.in_(payload.job_ids))).scalars()}
    if any(job_id not in jobs for job_id in payload.job_ids):
        raise HTTPException(404, "Job not found")
    if any(job.status != "completed" for job in jobs.values()):
        raise HTTPException(400, "Job processing has not completed")

    request = CVRequest(
        user_id=current_user.id,
        matching_ids=[],
        mode=payload.cv_mode,
        status="processing",
        job_ids=payload.job_ids,
        profile_id=profile.id,  # pinned now, so "latest profile" means latest at request time
        cover_letter_enabled=payload.cover_letter.enabled,
        cover_letter_mode=payload.cover_letter.mode if payload.cover_letter.enabled else None,
        output_language=payload.output_language,
    )
    db.add(request)
    db.flush()
    proc_job = ProcessingJob(user_id=current_user.id, job_type=ProcessingJobType.CV_TAILOR, result_id=request.id)
    db.add(proc_job)
    db.commit()
    db.refresh(proc_job)

    background_tasks.add_task(_run_tailoring, proc_job.id, request.id)
    return ProcessingJobOut(id=proc_job.id, status=proc_job.status.value, result_id=request.id)


@router.get("/tailoring/requests")
def list_tailoring_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    requests = (
        db.execute(
            select(CVRequest)
            .where(CVRequest.user_id == current_user.id, CVRequest.job_ids != [])
            .order_by(desc(CVRequest.created_at))
        )
        .scalars()
        .all()
    )
    return [_request_out(item) for item in requests]


@router.get("/tailoring/requests/{request_id}")
def get_tailoring_request(
    request_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    request = _owned_request(db, current_user.id, request_id)
    return _request_out(request, _request_documents(db, request.id))


@router.delete("/tailoring/requests/{request_id}", status_code=204)
def delete_tailoring_request(
    request_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    request = _owned_request(db, current_user.id, request_id)
    if request.status == "processing":
        raise HTTPException(409, "Tailoring request is still processing")
    for record in _request_documents(db, request.id):
        delete_tailored_record(db, record, delete_blob)
    db.delete(request)
    db.commit()


@router.delete("/tailoring/documents/{document_id}", status_code=204)
def delete_tailoring_document(
    document_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    record = db.get(TailoredCVRecord, document_id)
    if record is None or record.user_id != current_user.id:
        raise HTTPException(404, "Tailored document not found")
    delete_tailored_record(db, record, delete_blob)
