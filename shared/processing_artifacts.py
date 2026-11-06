import uuid

from sqlalchemy.orm import Session

from shared.models import ProcessingOutbox


def artifact_id(processing_job_id: str, index: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"processing-job:{processing_job_id}:artifact:{index}"))


def prepare_filenames(db: Session, processing_job_id: str, filenames: list[str]) -> list[str]:
    outbox = db.get(ProcessingOutbox, processing_job_id)
    if outbox is None:
        return filenames
    arguments = dict(outbox.arguments)
    stored = arguments.get("artifact_filenames")
    if stored is not None:
        if not isinstance(stored, list) or len(stored) != len(filenames) or not all(isinstance(s, str) for s in stored):
            raise ValueError("Invalid persisted artifact filenames")
        filenames = [previous or proposed for previous, proposed in zip(stored, filenames, strict=True)]
        if filenames == stored:
            return filenames
    arguments["artifact_filenames"] = filenames
    outbox.arguments = arguments
    db.commit()
    return filenames
