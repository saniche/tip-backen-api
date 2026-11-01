from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.openapi import error_responses
from api.schemas.requests.auth import UserCreate, UserLogin
from api.schemas.responses.auth import AuthTokenResponse
from auth.security import create_access_token, hash_password, verify_password
from shared.database import get_db
from shared.models import User

router = APIRouter(prefix="/auth")


@router.post(
    "/register",
    response_model=AuthTokenResponse,
    status_code=201,
    summary="Register an account",
    description="Creates an account and returns a bearer access token. Passwords are never returned.",
    tags=["Auth"],
    responses=error_responses(400, 422, 500),
)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(400, "Email already registered")

    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()

    return AuthTokenResponse(access_token=create_access_token(user.id))


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    status_code=200,
    summary="Log in",
    description="Validates JSON login credentials and returns a bearer access token.",
    tags=["Auth"],
    responses=error_responses(401, 422, 500),
)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == payload.username)).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(401, "Incorrect email or password")

    return AuthTokenResponse(access_token=create_access_token(user.id))
