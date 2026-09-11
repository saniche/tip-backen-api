from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import TailoredCVRecord, User
from storage import download_markdown

router = APIRouter(tags=["download"])


@router.get("/cv/{tailored_cv_id}/download")
@router.get("/download/{tailored_cv_id}")
def download_tailored_cv(
    tailored_cv_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.get(TailoredCVRecord, tailored_cv_id)
    if not record or record.user_id != current_user.id:
        raise HTTPException(404, "Tailored CV not found")

    content = download_markdown(record.blob_path)
    filename = record.blob_path.rsplit("/", 1)[-1]

    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
