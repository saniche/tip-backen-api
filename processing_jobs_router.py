from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import ProcessingJob, User
from schemas import ProcessingJobOut

router = APIRouter(prefix="/processing-jobs", tags=["processing-jobs"])


@router.get("/{job_id}", response_model=ProcessingJobOut)
def get_processing_job(job_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proc_job = db.get(ProcessingJob, job_id)
    if not proc_job or proc_job.user_id != current_user.id:
        raise HTTPException(404, "Job not found")

    return ProcessingJobOut(
        id=proc_job.id, status=proc_job.status.value, result_id=proc_job.result_id, error=proc_job.error
    )
