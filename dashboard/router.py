from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.openapi import error_responses
from api.schemas.common.dates import ISODate
from api.schemas.responses.dashboard import DashboardSummaryResponse
from auth.security import get_current_user
from dashboard.service import get_dashboard_summary
from shared.database import get_db
from shared.models import User

router = APIRouter(prefix="/dashboard")


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    status_code=200,
    summary="Get dashboard summary",
    description=(
        "Returns owned totals and due follow-ups. Supply today in the client's local timezone; "
        "otherwise the current UTC date is used."
    ),
    tags=["Dashboard"],
    responses=error_responses(401, 422, 500),
)
def dashboard_summary(
    today: ISODate | None = Query(
        default=None, description="Client's current date (YYYY-MM-DD); defaults to UTC today."
    ),
    follow_up_limit: int = Query(
        default=5, ge=1, description="Maximum due items; values above 100 are capped at 100."
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_dashboard_summary(
        db, current_user.id, today or datetime.now(timezone.utc).date(), min(follow_up_limit, 100)
    )
