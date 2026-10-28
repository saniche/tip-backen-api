from collections import OrderedDict
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from shared.models import UserProfile

PRECEDENCE = ["user_edited", "extracted", "inferred"]


def consolidate_profile_fragments(fragments):
    merged = OrderedDict()
    for fragment in fragments:
        data = fragment.get("data", {}) or {}
        source = fragment.get("evidence_type") or "extracted"
        for key, value in data.items():
            if key not in merged:
                merged[key] = {"value": value, "source": source}
                continue
            current = merged[key]
            if PRECEDENCE.index(source) < PRECEDENCE.index(current["source"]):
                merged[key] = {"value": value, "source": source}
    return {key: payload["value"] for key, payload in merged.items()}


def merge_profile_values(existing_data, existing_evidence, fragments):
    merged = consolidate_profile_fragments(fragments)
    evidence = dict(existing_evidence or {})
    for key, value in (existing_data or {}).items():
        if key == "__evidence__":
            continue
        if evidence.get(key) == "user_edited":
            merged[key] = value
    for fragment in fragments:
        source = fragment.get("evidence_type") or "extracted"
        for key in fragment.get("data") or {}:
            if evidence.get(key) != "user_edited":
                evidence[key] = source
    return merged, evidence


def list_profiles(db: Session, user_id: str) -> list[UserProfile]:
    """Active (not deleted) profiles, newest first. The first one is the default."""
    return list(
        db.execute(
            select(UserProfile)
            .where(UserProfile.user_id == user_id, UserProfile.deleted_at.is_(None))
            .order_by(desc(UserProfile.created_at), desc(UserProfile.id))
        )
        .scalars()
        .all()
    )


def get_owned_profile(db: Session, user_id: str, profile_id: str) -> UserProfile | None:
    profile = db.get(UserProfile, profile_id)
    if profile is None or profile.user_id != user_id or profile.deleted_at is not None:
        return None
    return profile


def resolve_profile(db: Session, user_id: str, profile_id: str | None = None) -> UserProfile:
    """The selected profile, or the latest active one when no profile is selected.

    Raises ValueError (callers translate it to 404/400) so background tasks can reuse it.
    """
    if profile_id is not None:
        profile = get_owned_profile(db, user_id, profile_id)
        if profile is None:
            raise ValueError("Profile not found")
        return profile
    profiles = list_profiles(db, user_id)
    if not profiles:
        raise ValueError("Profile not found")
    return profiles[0]


def apply_profile_edits(
    profile: UserProfile, data: dict | None, output_language: str | None, label: str | None
) -> None:
    """Merge user edits into a profile in place and mark the touched keys as user_edited."""
    if data:
        merged = dict(profile.data or {})
        for key, value in data.items():
            merged[key] = value["value"] if isinstance(value, dict) and "value" in value else value
        profile.data = merged
        evidence = dict(profile.evidence or {})
        evidence.update({key: "user_edited" for key in data})
        profile.evidence = evidence
    if output_language is not None:
        profile.output_language = output_language
    if label is not None:
        profile.label = label.strip() or None
    profile.updated_at = datetime.now(timezone.utc)


def soft_delete_profile(profile: UserProfile) -> None:
    profile.deleted_at = datetime.now(timezone.utc)
