"""Profile management: a user can own several profiles; the latest active one is the default."""

from profile.profile_service import (
    apply_profile_edits,
    get_owned_profile,
    list_profiles,
    soft_delete_profile,
)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth.security import get_current_user
from shared.database import get_db
from shared.models import User, UserProfile
from shared.schemas import ProfilePatch

router = APIRouter(tags=["profiles"])


def _serialize(profile: UserProfile, *, is_default: bool, include_data: bool) -> dict:
    payload = {
        "id": profile.id,
        "label": profile.label,
        "output_language": profile.output_language,
        "is_default": is_default,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }
    if include_data:
        payload["data"] = profile.data
    return payload


@router.get("/profiles")
def list_user_profiles(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profiles = list_profiles(db, current_user.id)
    return [_serialize(item, is_default=index == 0, include_data=False) for index, item in enumerate(profiles)]


@router.get("/profiles/{profile_id}")
def get_user_profile(profile_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_owned_profile(db, current_user.id, profile_id)
    if profile is None:
        raise HTTPException(404, "Profile not found")
    default_id = next(iter(item.id for item in list_profiles(db, current_user.id)[:1]), None)
    return _serialize(profile, is_default=profile.id == default_id, include_data=True)


@router.patch("/profiles/{profile_id}")
def update_user_profile(
    profile_id: str,
    payload: ProfilePatch,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = get_owned_profile(db, current_user.id, profile_id)
    if profile is None:
        raise HTTPException(404, "Profile not found")
    apply_profile_edits(profile, payload.data, payload.output_language, payload.label)
    db.commit()
    db.refresh(profile)
    default_id = next(iter(item.id for item in list_profiles(db, current_user.id)[:1]), None)
    return _serialize(profile, is_default=profile.id == default_id, include_data=True)


@router.delete("/profiles/{profile_id}", status_code=204)
def delete_user_profile(profile_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_owned_profile(db, current_user.id, profile_id)
    if profile is None:
        raise HTTPException(404, "Profile not found")
    soft_delete_profile(profile)
    db.commit()
