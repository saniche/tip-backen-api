from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.common.enums import (
    LegacyCvMode,
    TailoredDocumentKind,
    TailoredDocumentStatus,
    TailoringMode,
    TailoringRequestStatus,
)


class TailoredDocumentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Generated document identifier.", examples=["document-123"])
    kind: TailoredDocumentKind = Field(description="Generated document type.", examples=["cv"])
    scope: TailoringMode | LegacyCvMode = Field(
        description="Job scope used to generate the document.", examples=["per_job"]
    )
    job_id: str | None = Field(description="Single associated job identifier, when applicable.", examples=["job-123"])
    job_ids: list[str] = Field(description="Associated job identifiers.", examples=[["job-123"]])
    status: TailoredDocumentStatus = Field(description="Generation state.", examples=["completed"])
    error: str | None = Field(description="Safe failure message, if generation failed.", examples=[None])
    warning: str | None = Field(description="Non-fatal generation warning, if any.", examples=[None])
    filename: str | None = Field(
        description="Download filename, when the document is available.", examples=["software-engineer-cv.md"]
    )
    download_url: str | None = Field(
        description="Short-lived, read-only download URL when available.",
        examples=["https://example.invalid/download/temporary"],
    )
    created_at: datetime = Field(description="Document creation time.", examples=["2026-10-23T12:00:00Z"])


class CvTailoringResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "document-123",
                "matching_id": "matching-123",
                "download_url": "https://example.invalid/download/temporary",
            }
        },
    )

    id: str = Field(description="Generated CV identifier.", examples=["document-123"])
    matching_id: str = Field(description="Matching result used to generate the CV.", examples=["matching-123"])
    download_url: str = Field(
        description="Temporary download URL.", examples=["https://example.invalid/download/temporary"]
    )


class CvMetadataResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "document-123",
                "request_id": "request-123",
                "matching_id": "matching-123",
                "blob_path": "user-123/document-123/resume.md",
                "mode": "per_job",
                "status": "completed",
                "target_job_ids": ["job-123"],
                "download_url": "https://example.invalid/download/temporary",
            }
        },
    )

    id: str = Field(description="Generated CV identifier.", examples=["document-123"])
    request_id: str | None = Field(default=None, description="Tailoring request identifier.", examples=["request-123"])
    matching_id: str | None = Field(
        description="Matching result identifier, when directly associated.", examples=["matching-123"]
    )
    blob_path: str = Field(
        description="Stored document path retained for response compatibility.",
        examples=["user-123/document-123/resume.md"],
    )
    mode: LegacyCvMode | TailoringMode = Field(description="CV generation scope.", examples=["per_job"])
    status: TailoredDocumentStatus = Field(description="Generation state.", examples=["completed"])
    target_job_ids: list[str] = Field(description="Jobs used to tailor the CV.", examples=[["job-123"]])
    download_url: str = Field(
        description="Temporary download URL.", examples=["https://example.invalid/download/temporary"]
    )


class TailoringCoverLetterOptionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(description="Whether a cover letter was requested.", examples=[True])
    mode: TailoringMode | None = Field(description="Cover-letter generation scope.", examples=["per_job"])


class TailoringRequestSummaryResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "request-123",
                "status": "completed",
                "error": None,
                "job_ids": ["job-123"],
                "profile_id": "profile-123",
                "cv_mode": "per_job",
                "cover_letter": {"enabled": False, "mode": None},
                "output_language": "English",
                "created_at": "2026-10-23T12:00:00Z",
            }
        },
    )

    id: str = Field(description="Tailoring request identifier.", examples=["request-123"])
    status: TailoringRequestStatus = Field(description="Overall request state.", examples=["completed"])
    error: str | None = Field(description="Safe failure message, if any.", examples=[None])
    job_ids: list[str] = Field(description="Jobs selected for tailoring.", examples=[["job-123"]])
    profile_id: str | None = Field(description="Profile version selected for tailoring.", examples=["profile-123"])
    cv_mode: TailoringMode = Field(description="CV generation scope.", examples=["per_job"])
    cover_letter: TailoringCoverLetterOptionsResponse = Field(
        description="Cover-letter request settings.", examples=[{"enabled": False, "mode": None}]
    )
    output_language: str = Field(description="Language selected for generated documents.", examples=["English"])
    created_at: datetime = Field(description="Request creation time.", examples=["2026-10-23T12:00:00Z"])


class TailoringRequestDetailResponse(TailoringRequestSummaryResponse):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "request-123",
                "status": "completed",
                "error": None,
                "job_ids": ["job-123"],
                "profile_id": "profile-123",
                "cv_mode": "per_job",
                "cover_letter": {"enabled": False, "mode": None},
                "output_language": "English",
                "created_at": "2026-10-23T12:00:00Z",
                "documents": [],
            }
        },
    )

    documents: list[TailoredDocumentResponse] = Field(description="Documents generated by this request.", examples=[[]])
