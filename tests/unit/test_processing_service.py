from models import ProcessingJobStatus, ProcessingJobType
from processing_service import create_processing_job, fail_processing_job, start_processing_job


def test_processing_lifecycle(database_session):
    processing_job = create_processing_job(database_session, "user-1", ProcessingJobType.PROFILE_BUILD)
    start_processing_job(database_session, processing_job.id)
    assert processing_job.status == ProcessingJobStatus.RUNNING
    fail_processing_job(database_session, processing_job.id, "safe failure")
    assert processing_job.status == ProcessingJobStatus.FAILED
    assert processing_job.error == "safe failure"
