from sqlalchemy.orm import Session

from models import ProcessingJob, ProcessingJobStatus, ProcessingJobType


def create_processing_job(db: Session, user_id: str, job_type: ProcessingJobType) -> ProcessingJob:
    job = ProcessingJob(user_id=user_id, job_type=job_type)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def start_processing_job(db: Session, job_id: str) -> ProcessingJob:
    job = db.get(ProcessingJob, job_id)
    if job is None:
        raise ValueError("Processing job not found")
    job.status = ProcessingJobStatus.RUNNING
    db.commit()
    return job


def complete_processing_job(db: Session, job_id: str, result_id: str) -> ProcessingJob:
    job = db.get(ProcessingJob, job_id)
    if job is None:
        raise ValueError("Processing job not found")
    job.status = ProcessingJobStatus.DONE
    job.result_id = result_id
    job.error = None
    db.commit()
    return job


def fail_processing_job(db: Session, job_id: str, message: str) -> ProcessingJob:
    job = db.get(ProcessingJob, job_id)
    if job is None:
        raise ValueError("Processing job not found")
    job.status = ProcessingJobStatus.FAILED
    job.error = message
    db.commit()
    return job
