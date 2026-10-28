"""Default CV / default cover letter: at most one of each kind per user (PUT is an upsert)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.models import UserDocument

KIND_CV = "cv"
KIND_COVER_LETTER = "cover_letter"
KINDS = (KIND_CV, KIND_COVER_LETTER)
MAX_CONTENT_CHARS = 50_000


def get_default_document(db: Session, user_id: str, kind: str) -> UserDocument | None:
    return db.execute(
        select(UserDocument).where(UserDocument.user_id == user_id, UserDocument.kind == kind)
    ).scalar_one_or_none()


def upsert_default_document(db: Session, user_id: str, kind: str, content: str, filename: str | None) -> UserDocument:
    document = get_default_document(db, user_id, kind)
    if document is None:
        document = UserDocument(user_id=user_id, kind=kind, content=content, filename=filename)
        db.add(document)
    else:
        document.content = content
        document.filename = filename
    db.commit()
    db.refresh(document)
    return document


def delete_default_document(db: Session, user_id: str, kind: str) -> bool:
    document = get_default_document(db, user_id, kind)
    if document is None:
        return False
    db.delete(document)
    db.commit()
    return True
