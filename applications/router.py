from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from api.openapi import error_responses
from api.schemas.requests.applications import ApplicationCreate, ApplicationFieldsUpdate, ApplicationStatusUpdate
from api.schemas.responses.applications import ApplicationJournalPage, ApplicationJournalResponse
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

router = APIRouter(prefix="/applications")


@router.post(
    "",
    response_model=ApplicationJournalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an application entry",
    description="Starts tracking a normalized job in the authenticated user's application journal.",
    tags=["Applications"],
    responses=error_responses(401, 404, 409, 422, 500),
)
def create_application_entry(
    payload: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_application(db, current_user.id, payload)


@router.get(
    "",
    response_model=ApplicationJournalPage,
    status_code=status.HTTP_200_OK,
    summary="List application entries",
    description="Lists the authenticated user's application entries with optional job filters and pagination.",
    tags=["Applications"],
    responses=error_responses(401, 422, 500),
)
def list_application_entries(
    title: str | None = Query(default=None, description="Case-insensitive job-title filter.", examples=["Engineer"]),
    company: str | None = Query(default=None, description="Case-insensitive employer filter.", examples=["Example Co"]),
    location: str | None = Query(
        default=None, description="Case-insensitive job-location filter.", examples=["Remote"]
    ),
    page: int = Query(1, ge=1, description="One-based page number.", examples=[1]),
    limit: int = Query(20, ge=1, le=100, description="Maximum entries per page.", examples=[20]),
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


@router.get(
    "/{application_id}",
    response_model=ApplicationJournalResponse,
    status_code=status.HTTP_200_OK,
    summary="Get an application entry",
    description="Returns one application entry owned by the authenticated user.",
    tags=["Applications"],
    responses=error_responses(401, 404, 500),
)
def retrieve_application_entry(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_application(db, current_user.id, application_id)


@router.patch(
    "/{application_id}",
    response_model=ApplicationJournalResponse,
    status_code=status.HTTP_200_OK,
    summary="Update application details",
    description="Partially updates editable contact, date, and notes fields for an owned entry.",
    tags=["Applications"],
    responses=error_responses(401, 404, 422, 500),
)
def update_application_entry(
    application_id: str,
    payload: ApplicationFieldsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_application_fields(db, current_user.id, application_id, payload)


@router.patch(
    "/{application_id}/status",
    response_model=ApplicationJournalResponse,
    status_code=status.HTTP_200_OK,
    summary="Update application status",
    description="Changes the current status and appends a history entry when the status changes.",
    tags=["Applications"],
    responses=error_responses(401, 404, 422, 500),
)
def update_application_entry_status(
    application_id: str,
    payload: ApplicationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_application_status(db, current_user.id, application_id, payload)


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an application entry",
    description="Deletes an application entry owned by the authenticated user.",
    tags=["Applications"],
    responses=error_responses(401, 404, 500),
)
def remove_application_entry(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    delete_application(db, current_user.id, application_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
