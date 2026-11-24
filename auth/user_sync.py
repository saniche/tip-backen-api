"""Just-in-time provisioning of the local `users` row from validated Keycloak token claims."""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import shared.config as config
from shared.models import User

# Avoid a DB write on every request: only bump last_login_at when it is older than this.
LAST_LOGIN_REFRESH = timedelta(minutes=5)


def roles_from_claims(claims: dict[str, Any]) -> set[str]:
    roles = set((claims.get("realm_access") or {}).get("roles") or [])
    client_access = (claims.get("resource_access") or {}).get(config.KEYCLOAK_AUDIENCE) or {}
    roles.update(client_access.get("roles") or [])
    return roles


def role_from_claims(claims: dict[str, Any]) -> str:
    return "admin" if config.KEYCLOAK_ADMIN_ROLE in roles_from_claims(claims) else "user"


def _email_claim(claims: dict[str, Any]) -> str | None:
    email = claims.get("email")
    return email.strip() if isinstance(email, str) and email.strip() else None


def _user_with_email(db: Session, email: str) -> User | None:
    # Emails are compared case-insensitively (Keycloak lowercases them; legacy rows may not be).
    return db.execute(select(User).where(func.lower(User.email) == email.lower())).scalar_one_or_none()


def _apply_claims(user: User, claims: dict[str, Any], email: str, now: datetime) -> bool:
    """Copy identity attributes from the token onto the row. Returns True when anything changed."""
    desired = {
        "keycloak_sub": claims["sub"],
        "email": email,
        "email_verified": bool(claims.get("email_verified", False)),
        "username": claims.get("preferred_username"),
        "first_name": claims.get("given_name"),
        "last_name": claims.get("family_name"),
        "role": role_from_claims(claims),
    }
    changed = False
    for field, value in desired.items():
        if getattr(user, field) != value:
            setattr(user, field, value)
            changed = True
    last_login = user.last_login_at
    if last_login is not None and last_login.tzinfo is None:
        last_login = last_login.replace(tzinfo=timezone.utc)
    if last_login is None or now - last_login > LAST_LOGIN_REFRESH:
        user.last_login_at = now
        changed = True
    return changed


def _find_or_link(db: Session, sub: str, email: str, email_verified: bool) -> User | None:
    user = db.execute(select(User).where(User.keycloak_sub == sub)).scalar_one_or_none()
    if user is not None:
        return user

    by_email = _user_with_email(db, email)
    if by_email is None:
        return None
    if by_email.keycloak_sub is not None:
        # The address belongs to a different Keycloak identity already linked to this app.
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already linked to another account")
    if not email_verified:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Verify your email address in Keycloak to access your existing account"
        )
    return by_email  # legacy (pre-Keycloak) row: link it


def sync_user_from_claims(db: Session, claims: dict[str, Any]) -> User:
    sub = claims["sub"]
    email = _email_claim(claims)
    if email is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access token has no email claim")
    email_verified = bool(claims.get("email_verified", False))
    now = datetime.now(timezone.utc)

    user = _find_or_link(db, sub, email, email_verified)
    if user is not None and user.keycloak_sub == sub and user.email.lower() != email.lower():
        # Email changed in Keycloak; make sure the new address is not held by another row.
        holder = _user_with_email(db, email)
        if holder is not None and holder.id != user.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email is already linked to another account")

    if user is None:
        user = User()
        db.add(user)

    if _apply_claims(user, claims, email, now):
        try:
            db.commit()
        except IntegrityError:
            # A concurrent first request for the same identity created the row first.
            db.rollback()
            existing = db.execute(select(User).where(User.keycloak_sub == sub)).scalar_one_or_none()
            if existing is None:
                raise HTTPException(status.HTTP_409_CONFLICT, "Email is already linked to another account")
            return existing
        db.refresh(user)
    return user
