from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from auth import get_current_user
from database import SessionLocal, get_db
from models import ProfileFileStatus, ProfileFragment, ProfileSession, ProfileSessionStatus, User, UserFile, UserProfile
from processing_service import create_processing_job, complete_processing_job, fail_processing_job, start_processing_job
from models import ProcessingJobType
from pipeline.profile_builder import extract_profile
from profile_service import merge_profile_values

router = APIRouter(prefix="", tags=["profile"])


class ProfileUpdate(BaseModel):
    data: dict
    output_language: str = "English"


def _run_profile_session(session_id: str, user_id: str, processing_job_id: str) -> None:
    db = SessionLocal()
    try:
        session = db.get(ProfileSession, session_id)
        start_processing_job(db, processing_job_id)
        session.status = ProfileSessionStatus.PROCESSING
        db.commit()
        files = db.execute(select(UserFile).where(UserFile.session_id == session_id)).scalars().all()
        fragments = []
        for file in files:
            file.status = ProfileFileStatus.PROCESSING
            extracted = extract_profile({"content": file.content, "name": file.filename})
            fragment_data = {
                "name": extracted.Name,
                "summary": extracted.Summary,
                "skills": [item.Name for item in extracted.TechnicalSkills],
                "languages": extracted.Languages,
                "source": file.filename,
            }
            db.add(ProfileFragment(file_id=file.id, data=fragment_data, evidence_type="extracted"))
            fragments.append({"data": fragment_data, "evidence_type": "extracted"})
            file.status = ProfileFileStatus.COMPLETED
        previous = db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id).order_by(desc(UserProfile.created_at))
        ).scalars().first()
        previous_data = previous.data if previous else {}
        previous_evidence = previous.evidence if previous else {}
        merged, evidence = merge_profile_values(previous_data, previous_evidence, fragments)
        profile = UserProfile(user_id=user_id, data=merged, evidence=evidence, output_language="English")
        db.add(profile)
        db.flush()
        session.status = ProfileSessionStatus.COMPLETED
        db.commit()
        complete_processing_job(db, processing_job_id, profile.id)
    except Exception:
        session = db.get(ProfileSession, session_id)
        if session:
            session.status = ProfileSessionStatus.FAILED
        db.commit()
        fail_processing_job(db, processing_job_id, "Profile processing failed")
    finally:
        db.close()


@router.post("/profile/sessions", status_code=201)
def create_profile_session(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    session = ProfileSession(user_id=current_user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id, "status": session.status.value}


@router.post("/profile/sessions/{session_id}/files", status_code=202)
async def upload_profile_file(
    session_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.get(ProfileSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(404, "Profile session not found")
    if file.content_type not in {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"}:
        raise HTTPException(422, "Unsupported file type")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(422, "File exceeds maximum size")
    user_file = UserFile(user_id=current_user.id, session_id=session.id, filename=file.filename or "document", content_type=file.content_type, content=content.decode("utf-8", errors="replace"))
    db.add(user_file)
    processing_job = create_processing_job(db, current_user.id, ProcessingJobType.PROFILE_BUILD)
    db.commit()
    background_tasks.add_task(_run_profile_session, session.id, current_user.id, processing_job.id)
    return {"file_id": user_file.id, "processing_job_id": processing_job.id, "status": processing_job.status.value}


@router.get("/profile/sessions/{session_id}")
def get_profile_session(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.get(ProfileSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(404, "Profile session not found")
    files = db.execute(select(UserFile).where(UserFile.session_id == session.id)).scalars().all()
    return {"id": session.id, "status": session.status.value, "files": [{"id": item.id, "status": item.status.value, "error": item.error} for item in files]}


@router.get("/profile")
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id).order_by(desc(UserProfile.created_at))
    ).scalars().first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"id": profile.id, "user_id": profile.user_id, "data": profile.data, "output_language": profile.output_language}


@router.put("/profile")
def update_profile(payload: ProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id).order_by(desc(UserProfile.created_at))).scalars().first()
    if profile is None:
        profile = UserProfile(user_id=current_user.id, data={}, evidence={}, output_language=payload.output_language)
        db.add(profile)
    merged = dict(profile.data)
    for key, value in payload.data.items():
        if isinstance(value, dict) and "value" in value:
            merged[key] = value["value"]
        else:
            merged[key] = value
    profile.data = merged
    profile.evidence = dict(profile.evidence or {})
    profile.evidence.update({key: "user_edited" for key in payload.data})
    profile.output_language = payload.output_language
    db.commit()
    db.refresh(profile)
    return {"id": profile.id, "user_id": profile.user_id, "data": profile.data, "output_language": profile.output_language}
