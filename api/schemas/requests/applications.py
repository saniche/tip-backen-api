from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from api.schemas.common.enums import ApplicationStatus
from api.schemas.common.value_objects import RecruiterInfo


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "jobId": "job-123",
                "recruiterInfo": {"name": "Alex Recruiter"},
                "contactDate": "2026-10-22",
                "followUpDate": "2026-10-29",
                "workAuthorizationDiscussed": False,
                "notes": "Applied through the company careers page",
            }
        },
    )

    job_id: str = Field(
        validation_alias="jobId",
        serialization_alias="jobId",
        description="Identifier of the normalized job being tracked.",
        examples=["job-123"],
    )
    recruiter_info: RecruiterInfo | None = Field(
        default=None,
        validation_alias="recruiterInfo",
        serialization_alias="recruiterInfo",
        description="Optional recruiter contact details.",
        examples=[{"name": "Alex Recruiter", "email": "alex@example.com", "phone": "+1-555-0100"}],
    )
    contact_date: date | None = Field(
        default=None,
        validation_alias="contactDate",
        serialization_alias="contactDate",
        description="Date of the latest contact.",
        examples=["2026-10-22"],
    )
    follow_up_date: date | None = Field(
        default=None,
        validation_alias="followUpDate",
        serialization_alias="followUpDate",
        description="Planned follow-up date.",
        examples=["2026-10-29"],
    )
    work_authorization_discussed: bool = Field(
        default=False,
        validation_alias="workAuthorizationDiscussed",
        serialization_alias="workAuthorizationDiscussed",
        description="Whether work authorization was discussed.",
        examples=[False],
    )
    notes: str | None = Field(
        default=None, description="Optional application notes.", examples=["Recruiter follow-up scheduled."]
    )


class ApplicationFieldsUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "recruiterInfo": {"name": "Alex Recruiter"},
                "contactDate": "2026-10-22",
                "workAuthorizationDiscussed": True,
                "notes": "Sent a follow-up email",
            }
        },
    )

    recruiter_info: RecruiterInfo | None = Field(
        default=None,
        validation_alias="recruiterInfo",
        serialization_alias="recruiterInfo",
        description="Replacement recruiter details, or null to clear.",
        examples=[{"name": "Alex Recruiter"}],
    )
    contact_date: date | None = Field(
        default=None,
        validation_alias="contactDate",
        serialization_alias="contactDate",
        description="Updated contact date, or null to clear.",
        examples=["2026-10-22"],
    )
    follow_up_date: date | None = Field(
        default=None,
        validation_alias="followUpDate",
        serialization_alias="followUpDate",
        description="Updated follow-up date, or null to clear.",
        examples=["2026-10-29"],
    )
    work_authorization_discussed: bool = Field(
        default=None,
        validation_alias="workAuthorizationDiscussed",
        serialization_alias="workAuthorizationDiscussed",
        description="Whether work authorization was discussed.",
        examples=[True],
    )
    notes: str | None = Field(
        default=None, description="Updated notes, or null to clear.", examples=["Sent a follow-up email"]
    )

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("At least one editable field must be provided")
        return self


class ApplicationStatusUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid", json_schema_extra={"example": {"status": "Interview", "note": "Technical interview scheduled"}}
    )

    status: ApplicationStatus = Field(description="New application status.", examples=["Interview"])
    note: str | None = Field(
        default=None,
        description="Optional note recorded with the status change.",
        examples=["Technical interview scheduled"],
    )
