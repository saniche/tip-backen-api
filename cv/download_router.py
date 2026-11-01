from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from api.openapi import error_responses
from auth.security import get_current_user
from shared.database import get_db
from shared.models import TailoredCVRecord, User
from shared.storage import download_markdown, generate_temporary_download_url

router = APIRouter()


@router.get(
    "/cv/{tailored_cv_id}/download",
    response_model=None,
    response_class=Response,
    status_code=200,
    summary="Download a tailored CV",
    description=(
        "Returns an owned completed tailored document as Markdown; the response includes "
        "attachment and temporary URL headers."
    ),
    tags=["Documents"],
    responses={
        200: {
            "description": "Markdown document bytes.",
            "content": {"text/markdown": {"schema": {"type": "string", "format": "binary"}}},
            "headers": {
                "Content-Disposition": {
                    "description": "Suggested attachment filename.",
                    "schema": {"type": "string"},
                },
                "X-Temporary-Download-URL": {
                    "description": "Short-lived read-only download capability URL.",
                    "schema": {"type": "string", "format": "uri"},
                },
            },
        },
        **error_responses(401, 404, 500, 503),
    },
)
@router.get(
    "/tailoring/documents/{tailored_cv_id}/download",
    response_model=None,
    response_class=Response,
    status_code=200,
    summary="Download a tailored document",
    description="Compatibility alias that returns an owned completed document as Markdown.",
    tags=["Documents"],
    responses={
        200: {
            "description": "Markdown document bytes.",
            "content": {"text/markdown": {"schema": {"type": "string", "format": "binary"}}},
            "headers": {
                "Content-Disposition": {
                    "description": "Suggested attachment filename.",
                    "schema": {"type": "string"},
                },
                "X-Temporary-Download-URL": {
                    "description": "Short-lived read-only download capability URL.",
                    "schema": {"type": "string", "format": "uri"},
                },
            },
        },
        **error_responses(401, 404, 500, 503),
    },
)
def download_tailored_cv(
    tailored_cv_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.get(TailoredCVRecord, tailored_cv_id)
    if not record or record.user_id != current_user.id:
        raise HTTPException(404, "Tailored document not found")
    if record.status != "completed" or not record.blob_path:
        raise HTTPException(404, "Tailored document is not available")

    content = download_markdown(record.blob_path)
    filename = record.blob_path.rsplit("/", 1)[-1]

    return Response(
        content=content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Temporary-Download-URL": generate_temporary_download_url(record.blob_path),
        },
    )
