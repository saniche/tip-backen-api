from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.openapi import error_responses
from api.schemas.requests.documents import DefaultDocumentIn
from api.schemas.responses.documents import DefaultDocumentResponse
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
from shared.document_text import (
    DocumentTextError,
    detect_document_type,
    extract_document_text,
    safe_filename,
)
from shared.models import User, UserDocument

router = APIRouter()

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _serialize(document: UserDocument) -> dict:
    return {
        "kind": document.kind,
        "content": document.content,
        "filename": document.filename,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


async def _text_from_upload(file: UploadFile) -> str:
    document_type = detect_document_type(file.content_type, file.filename)
    if document_type is None:
        raise HTTPException(422, "Unsupported file type: upload a .docx, .md or .txt file")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(422, "File exceeds maximum size")
    try:
        text = extract_document_text(content, document_type, preserve_structure=True).strip()
    except DocumentTextError as error:
        raise HTTPException(422, str(error)) from error
    if not text:
        raise HTTPException(422, "No text could be extracted from the file")
    if len(text) > MAX_CONTENT_CHARS:
        raise HTTPException(422, f"Document is too long (maximum {MAX_CONTENT_CHARS:,} characters)")
    return text


def _register(path: str, kind: str, label: str) -> None:
    @router.get(
        path,
        response_model=DefaultDocumentResponse,
        status_code=200,
        summary=f"Get default {label}",
        description=f"Returns the authenticated user's saved default {label}.",
        tags=["Documents"],
        responses=error_responses(401, 404, 500),
        name=f"get_default_{kind}",
    )
    def read(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        document = get_default_document(db, current_user.id, kind)
        if document is None:
            raise HTTPException(404, f"Default {label} not found")
        return _serialize(document)

    @router.put(
        path,
        response_model=DefaultDocumentResponse,
        status_code=200,
        summary=f"Save default {label}",
        description=f"Creates or replaces the authenticated user's default {label}.",
        tags=["Documents"],
        responses=error_responses(401, 422, 500),
        name=f"put_default_{kind}",
    )
    def write(
        payload: DefaultDocumentIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ):
        return _serialize(upsert_default_document(db, current_user.id, kind, payload.content, payload.filename))

    @router.post(
        f"{path}/file",
        response_model=DefaultDocumentResponse,
        status_code=200,
        summary=f"Upload default {label}",
        description=(
            f"Extracts text from a supported DOCX, Markdown, or TXT upload and saves it as the default {label}."
        ),
        tags=["Documents"],
        responses=error_responses(401, 422, 500, 503),
        name=f"upload_default_{kind}",
    )
    async def upload(
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        text = await _text_from_upload(file)
        return _serialize(upsert_default_document(db, current_user.id, kind, text, safe_filename(file.filename)))

    @router.delete(
        path,
        status_code=204,
        summary=f"Delete default {label}",
        description=f"Deletes the authenticated user's saved default {label}.",
        tags=["Documents"],
        responses=error_responses(401, 404, 500),
        name=f"delete_default_{kind}",
    )
    def remove(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        if not delete_default_document(db, current_user.id, kind):
            raise HTTPException(404, f"Default {label} not found")


_register("/defaults/cv", KIND_CV, "CV")
_register("/defaults/cover-letter", KIND_COVER_LETTER, "cover letter")
