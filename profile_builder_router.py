from dataclasses import asdict

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy.orm import Session

from auth import get_current_user
from database import SessionLocal, get_db
from models import ProcessingJob, ProcessingJobStatus, ProcessingJobType, User, UserProfile
from pipeline.profile_builder import build_user_profile, extract_partial_profile
from schemas import ProcessingJobOut

router = APIRouter(prefix="/profile-builder", tags=["profile-builder"])


def _run_profile_build(
    proc_job_id: str,
    user_id: str,
    files: list[tuple[str, str, str]],  # (filename, text_content, file_type)
    output_language: str,
) -> None:
    """Runs in the background (BackgroundTasks) — needs its own DB session, not the request's."""
    db = SessionLocal()
    try:
        proc_job = db.get(ProcessingJob, proc_job_id)
        proc_job.status = ProcessingJobStatus.RUNNING
        db.commit()

        partials = [extract_partial_profile(text, filename, file_type) for filename, text, file_type in files]
        profile = build_user_profile(partials, output_language)

        db_profile = UserProfile(user_id=user_id, data=asdict(profile), output_language=output_language)
        db.add(db_profile)
        db.commit()

        proc_job.status = ProcessingJobStatus.DONE
        proc_job.result_id = db_profile.id
        db.commit()
    except Exception as e:  # noqa: BLE001 — surface any failure via the polled status, don't crash the worker
        proc_job.status = ProcessingJobStatus.FAILED
        proc_job.error = str(e)
        db.commit()
    finally:
        db.close()


@router.post("/build", response_model=ProcessingJobOut)
async def build_profile(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    file_types: list[str] | None = None,  # aligned by index with `files`; defaults to "other"
    output_language: str = "English",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    proc_job = ProcessingJob(user_id=current_user.id, job_type=ProcessingJobType.PROFILE_BUILD)
    db.add(proc_job)
    db.commit()

    file_payload = []
    for i, f in enumerate(files):
        content = (await f.read()).decode("utf-8")
        ftype = file_types[i] if file_types and i < len(file_types) else "other"
        file_payload.append((f.filename, content, ftype))

    background_tasks.add_task(_run_profile_build, proc_job.id, current_user.id, file_payload, output_language)

    return ProcessingJobOut(id=proc_job.id, status=proc_job.status.value)
