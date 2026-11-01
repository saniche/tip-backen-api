from pydantic import BaseModel, ConfigDict, Field, model_validator

from api.schemas.common.enums import LegacyCvMode, TailoringMode


class CvTailoringRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"matching_ids": ["matching-123"], "mode": "per_job", "output_language": "English"}
        },
    )

    matching_ids: list[str] = Field(
        default_factory=list, description="Matching result identifiers to tailor.", examples=[["matching-123"]]
    )
    mode: LegacyCvMode = Field(
        default=LegacyCvMode.PER_JOB,
        description="Whether to generate one CV per job or one for the full group.",
        examples=["group_all"],
    )
    output_language: str = Field(
        default="English", description="Language for generated CV content.", examples=["English"]
    )
    matching_id: str | None = Field(
        default=None,
        description="Legacy single matching identifier; use matching_ids for new clients.",
        examples=["matching-123"],
    )

    @model_validator(mode="after")
    def validate_selection(self):
        if self.matching_id and not self.matching_ids:
            self.matching_ids = [self.matching_id]
        if not self.matching_ids:
            raise ValueError("At least one matching result is required")
        return self


class CoverLetterOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": {"enabled": True, "mode": "per_job"}})

    enabled: bool = Field(default=False, description="Whether to generate a cover letter.", examples=[True])
    mode: TailoringMode | None = Field(
        default=None, description="Cover-letter scope when enabled.", examples=["per_job"]
    )


class TailoringRequestIn(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "job_ids": ["job-123"],
                "profile_id": "profile-123",
                "cv_mode": "per_job",
                "cover_letter": {"enabled": True, "mode": "per_job"},
                "output_language": "English",
            }
        },
    )

    job_ids: list[str] = Field(
        min_length=1, max_length=10, description="One to ten normalized job identifiers.", examples=[["job-123"]]
    )
    profile_id: str | None = Field(
        default=None, description="Profile to use; null selects the latest active profile.", examples=["profile-123"]
    )
    cv_mode: TailoringMode = Field(
        default=TailoringMode.PER_JOB, description="CV generation scope.", examples=["per_job"]
    )
    cover_letter: CoverLetterOptions = Field(
        default_factory=CoverLetterOptions,
        description="Optional cover-letter generation settings.",
        examples=[{"enabled": True, "mode": "per_job"}],
    )
    output_language: str = Field(
        default="English", description="Language for generated documents.", examples=["English"]
    )

    @model_validator(mode="after")
    def validate_request(self):
        self.job_ids = list(dict.fromkeys(self.job_ids))
        if self.cover_letter.enabled and self.cover_letter.mode is None:
            raise ValueError("cover_letter.mode is required when the cover letter is enabled")
        return self
