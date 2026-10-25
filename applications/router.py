from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from applications.application_service import (
    create_application,
    delete_application,
    get_application,
    list_applications,
    update_application_fields,
    update_application_status,
)
from auth.security import get_current_user
from shared.database import get_db
from shared.models import User
from shared.schemas import (
    ApplicationCreate,
    ApplicationFieldsUpdate,
    ApplicationJournalItem,
    ApplicationJournalPage,
    ApplicationStatusUpdate,
)

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=ApplicationJournalItem, status_code=status.HTTP_201_CREATED)
def create_application_entry(
    payload: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_application(db, current_user.id, payload)


@router.get("", response_model=ApplicationJournalPage)
def list_application_entries(
    title: str | None = None,
    company: str | None = None,
    location: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_applications(
        db,
        current_user.id,
        title=title,
        company=company,
        location=location,
        page=page,
        limit=limit,
    )


@router.get("/{application_id}", response_model=ApplicationJournalItem)
def retrieve_application_entry(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_application(db, current_user.id, application_id)


@router.patch("/{application_id}", response_model=ApplicationJournalItem)
def update_application_entry(
    application_id: str,
    payload: ApplicationFieldsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_application_fields(db, current_user.id, application_id, payload)


@router.patch("/{application_id}/status", response_model=ApplicationJournalItem)
def update_application_entry_status(
    application_id: str,
    payload: ApplicationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_application_status(db, current_user.id, application_id, payload)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_application_entry(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    delete_application(db, current_user.id, application_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
