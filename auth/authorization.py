from fastapi import HTTPException, status


def require_owner_or_admin(*, owner_id: str, current_user) -> None:
    if current_user.id == owner_id or getattr(current_user, "role", "user") == "admin":
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
