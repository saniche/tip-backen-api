from fastapi import APIRouter, Depends

from api.openapi import error_responses
from api.schemas.responses.auth import CurrentUserResponse
from auth.security import get_current_user
from shared.models import User

router = APIRouter(prefix="/auth")


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    status_code=200,
    summary="Get the current user",
    description=(
        "Returns the local user record for the Keycloak identity in the bearer token. The record is created "
        "on the first authenticated request and kept in sync with the token claims. Sign-in and registration "
        "happen in Keycloak, not in this API."
    ),
    tags=["Auth"],
    responses=error_responses(401, 403, 409, 500, 503),
)
def me(current_user: User = Depends(get_current_user)):
    return current_user
