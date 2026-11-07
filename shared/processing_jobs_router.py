from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.openapi import error_responses
from api.schemas.responses.processing import ProcessingJobResponse
from auth.security import get_current_user
from shared.database import get_db
from shared.models import ProcessingJob, User

router = APIRouter(prefix="/processing-jobs")


@router.get(
    "/{job_id}",
    response_model=ProcessingJobResponse,
    status_code=200,
    summary="Get processing status",
    description="Returns an owned processing job's state, result identifier, or safe failure message.",
    tags=["Processing Jobs"],
    responses=error_responses(401, 404, 500),
)
def get_processing_job(job_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proc_job = db.get(ProcessingJob, job_id)
    if not proc_job or proc_job.user_id != current_user.id:
        raise HTTPException(404, "Job not found")

    return ProcessingJobResponse(
        id=proc_job.id, status=proc_job.status.value, result_id=proc_job.result_id, error=proc_job.error
    )
