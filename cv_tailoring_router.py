from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from auth import get_current_user
from database import SessionLocal, get_db
from models import Job, JobMatchingResult, ProcessingJob, ProcessingJobStatus, ProcessingJobType, TailoredCVRecord, User, UserProfile
from pipeline.cv_tailoring import build_tailored_cv
from pipeline.llm_matching import JobData
from pipeline.markdown_writer import render_tailored_cv_markdown, suggest_filename
from schemas import CvTailoringRequest, ProcessingJobOut
from serialization import dict_to_user_profile
from storage import build_blob_path, upload_markdown

router = APIRouter(tags=["cv-tailoring"])


def _run_cv_tailoring(proc_job_id: str, user_id: str, matching_id: str, output_language: str) -> None:
    db = SessionLocal()
    proc_job = None
    try:
        proc_job = db.get(ProcessingJob, proc_job_id)
        if proc_job is None:
            return
        proc_job.status = ProcessingJobStatus.RUNNING
        db.commit()

        matching = db.get(JobMatchingResult, matching_id)
        if matching is None:
            raise ValueError("Matching result not found")
        job = db.get(Job, matching.job_id)
        profile_row = db.get(UserProfile, matching.profile_id)  # same version the match was scored against
        if job is None or profile_row is None:
            raise ValueError("Matching context not found")
        profile = dict_to_user_profile(profile_row.data)

        job_data = JobData(
            title=job.title,
            required=job.required,
            desirable=job.desirable,
            technical_stack=job.technical_stack,
            key_responsibilities=job.key_responsibilities,
            summary=job.summary,
        )

        tailored = build_tailored_cv(profile, job_data, match_score=matching.score, output_language=output_language)
        markdown = render_tailored_cv_markdown(tailored)

        record = TailoredCVRecord(matching_id=matching.id, user_id=user_id, blob_path="")
        db.add(record)
        db.flush()  # assigns record.id before we build the blob path

        blob_path = build_blob_path(user_id, record.id, suggest_filename(tailored))
        upload_markdown(blob_path, markdown)
        record.blob_path = blob_path
        db.commit()

        proc_job.status = ProcessingJobStatus.DONE
        proc_job.result_id = record.id
        db.commit()
    except Exception as e:  # noqa: BLE001 — surface via polled status
        if proc_job is not None:
            proc_job.status = ProcessingJobStatus.FAILED
            proc_job.error = str(e)
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
    matching = db.get(JobMatchingResult, payload.matching_id)
    if not matching or matching.user_id != current_user.id:
        raise HTTPException(404, "Matching result not found")

    proc_job = ProcessingJob(user_id=current_user.id, job_type=ProcessingJobType.CV_TAILOR)
    db.add(proc_job)
    db.commit()

    background_tasks.add_task(
        _run_cv_tailoring, proc_job.id, current_user.id, matching.id, payload.output_language
    )

    return ProcessingJobOut(id=proc_job.id, status=proc_job.status.value, result_id=proc_job.result_id)


@router.get("/cv")
def list_cvs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cvs = db.execute(
        select(TailoredCVRecord).where(TailoredCVRecord.user_id == current_user.id).order_by(desc(TailoredCVRecord.created_at))
    ).scalars().all()
    return [{"id": item.id, "matching_id": item.matching_id, "blob_path": item.blob_path} for item in cvs]


@router.get("/cv/{tailored_cv_id}")
def get_cv(tailored_cv_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.get(TailoredCVRecord, tailored_cv_id)
    if not record or record.user_id != current_user.id:
        raise HTTPException(404, "Tailored CV not found")
    return {"id": record.id, "matching_id": record.matching_id, "blob_path": record.blob_path}


@router.delete("/cv/{tailored_cv_id}", status_code=204)
def delete_cv(tailored_cv_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.get(TailoredCVRecord, tailored_cv_id)
    if not record or record.user_id != current_user.id:
        raise HTTPException(404, "Tailored CV not found")
    db.delete(record)
    db.commit()
