from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.common.enums import ProfileFileStatus, ProfileSessionStatus


class ProfileSessionResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"id": "session-123", "status": "created", "output_language": "English"}},
    )

    id: str = Field(description="Profile-building session identifier.", examples=["session-123"])
    status: ProfileSessionStatus = Field(description="Current profile session state.", examples=["created"])
    output_language: str = Field(description="Language selected for profile extraction.", examples=["English"])


class ProfileFileUploadResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {"file_id": "file-123", "processing_job_id": "processing-123", "status": "pending"}
        },
    )

    file_id: str = Field(description="Uploaded profile file identifier.", examples=["file-123"])
    processing_job_id: str = Field(description="Processing job identifier to poll.", examples=["processing-123"])
    status: ProfileFileStatus = Field(description="Current file-processing state.", examples=["pending"])


class ProfileSessionFileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Uploaded file identifier.", examples=["file-123"])
    status: ProfileFileStatus = Field(description="Current file-processing state.", examples=["completed"])
    error: str | None = Field(description="Safe processing failure message, if any.", examples=[None])


class ProfileSessionDetailResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {"id": "session-123", "status": "completed", "output_language": "English", "files": []}
        },
    )

    id: str = Field(description="Profile-building session identifier.", examples=["session-123"])
    status: ProfileSessionStatus = Field(description="Current profile session state.", examples=["completed"])
    output_language: str = Field(description="Language selected for profile extraction.", examples=["English"])
    files: list[ProfileSessionFileResponse] = Field(description="Files associated with this session.", examples=[[]])


class CurrentProfileResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "profile-123",
                "user_id": "user-123",
                "data": {"summary": "Python engineer"},
                "output_language": "English",
                "label": "Engineering profile",
            }
        },
    )

    id: str = Field(description="Profile identifier.", examples=["profile-123"])
    user_id: str = Field(
        description="Owning account identifier, retained for response compatibility.", examples=["user-123"]
    )
    data: dict[str, Any] = Field(
        description="Structured profile information.", examples=[{"summary": "Python engineer"}]
    )
    output_language: str = Field(description="Language used for the profile.", examples=["English"])
    label: str | None = Field(description="Optional profile display label.", examples=["Engineering profile"])


class UserProfileSummaryResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "profile-123",
                "label": "Engineering",
                "output_language": "English",
                "is_default": True,
                "created_at": "2026-10-23T12:00:00Z",
                "updated_at": "2026-10-23T12:00:00Z",
            }
        },
    )

    id: str = Field(description="Profile identifier.", examples=["profile-123"])
    label: str | None = Field(description="Optional profile display label.", examples=["Engineering"])
    output_language: str = Field(description="Language used for the profile.", examples=["English"])
    is_default: bool = Field(description="Whether this is the current default profile.", examples=[True])
    created_at: datetime = Field(description="Profile creation time.", examples=["2026-10-23T12:00:00Z"])
    updated_at: datetime | None = Field(
        description="Most recent profile update time.", examples=["2026-10-23T12:00:00Z"]
    )


class UserProfileDetailResponse(UserProfileSummaryResponse):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "profile-123",
                "label": "Engineering",
                "output_language": "English",
                "is_default": True,
                "created_at": "2026-10-23T12:00:00Z",
                "updated_at": "2026-10-23T12:00:00Z",
                "data": {"summary": "Python engineer"},
            }
        },
    )

    data: dict[str, Any] = Field(
        description="Structured profile information.", examples=[{"summary": "Python engineer"}]
    )
