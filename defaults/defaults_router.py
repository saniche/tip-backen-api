from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from auth.security import get_current_user
from defaults.defaults_service import (
    KIND_COVER_LETTER,
    KIND_CV,
    MAX_CONTENT_CHARS,
    delete_default_document,
    get_default_document,
    upsert_default_document,
)
from shared.database import get_db
from shared.models import User, UserDocument

router = APIRouter(tags=["defaults"])


class DefaultDocumentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(max_length=MAX_CONTENT_CHARS)
    filename: str | None = Field(default=None, max_length=200)

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be empty")
        return value


def _serialize(document: UserDocument) -> dict:
    return {
        "kind": document.kind,
        "content": document.content,
        "filename": document.filename,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


def _register(path: str, kind: str, label: str) -> None:
    @router.get(path, name=f"get_default_{kind}")
    def read(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        document = get_default_document(db, current_user.id, kind)
        if document is None:
            raise HTTPException(404, f"Default {label} not found")
        return _serialize(document)

    @router.put(path, name=f"put_default_{kind}")
    def write(
        payload: DefaultDocumentIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ):
        return _serialize(upsert_default_document(db, current_user.id, kind, payload.content, payload.filename))

    @router.delete(path, status_code=204, name=f"delete_default_{kind}")
    def remove(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        if not delete_default_document(db, current_user.id, kind):
            raise HTTPException(404, f"Default {label} not found")


_register("/defaults/cv", KIND_CV, "CV")
_register("/defaults/cover-letter", KIND_COVER_LETTER, "cover letter")
