from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.common.enums import ApplicationStatus
from api.schemas.common.value_objects import RecruiterInfo


class ApplicationStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: datetime = Field(description="When this status was recorded.", examples=["2026-10-23T12:00:00Z"])
    note: str | None = Field(
        default=None, description="Optional note recorded with the status.", examples=["Technical interview scheduled"]
    )
    status: ApplicationStatus = Field(
        description="Application status at this point in history.", examples=["Interview"]
    )


class ApplicationJobHeaderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(description="Public job identifier.", examples=["job-123"])
    title: str = Field(description="Job title.", examples=["Software Engineer"])
    company: str | None = Field(description="Employer name.", examples=["Example Co"])
    location: str | None = Field(description="Job location.", examples=["Remote"])
    url: str | None = Field(description="Source job posting URL.", examples=["https://example.com/jobs/1"])
    source: str | None = Field(description="Source board or employer.", examples=["CompanyWebsite"])
    posting_date: str | None = Field(
        serialization_alias="postingDate", description="Source posting date.", examples=["2026-10-01"]
    )


class ApplicationJournalResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "application-123",
                "jobId": "job-123",
                "recruiterInfo": None,
                "contactDate": None,
                "followUpDate": None,
                "workAuthorizationDiscussed": False,
                "notes": None,
                "status": "NotStarted",
                "history": [],
                "createdAt": "2026-10-23T12:00:00Z",
                "updatedAt": "2026-10-23T12:00:00Z",
                "job": {
                    "id": "job-123",
                    "title": "Software Engineer",
                    "company": "Example Co",
                    "location": "Remote",
                    "url": "https://example.com/jobs/1",
                    "source": "CompanyWebsite",
                    "postingDate": "2026-10-01",
                },
            }
        },
    )

    id: str = Field(description="Application journal entry identifier.", examples=["application-123"])
    job_id: str = Field(serialization_alias="jobId", description="Identifier of the tracked job.", examples=["job-123"])
    recruiter_info: RecruiterInfo | None = Field(
        serialization_alias="recruiterInfo", description="Recruiter contact details, if provided.", examples=[None]
    )
    contact_date: date | None = Field(
        serialization_alias="contactDate", description="Most recent contact date.", examples=["2026-10-22"]
    )
    follow_up_date: date | None = Field(
        serialization_alias="followUpDate", description="Planned follow-up date.", examples=["2026-10-29"]
    )
    work_authorization_discussed: bool = Field(
        serialization_alias="workAuthorizationDiscussed",
        description="Whether work authorization was discussed.",
        examples=[False],
    )
    notes: str | None = Field(description="Application notes.", examples=["Applied through the company careers page"])
    status: ApplicationStatus = Field(description="Current application status.", examples=["NotStarted"])
    history: list[ApplicationStatusHistoryResponse] = Field(
        description="Chronological application status history.", examples=[[]]
    )
    created_at: datetime = Field(
        serialization_alias="createdAt", description="Entry creation time.", examples=["2026-10-23T12:00:00Z"]
    )
    updated_at: datetime = Field(
        serialization_alias="updatedAt", description="Most recent entry update time.", examples=["2026-10-23T12:00:00Z"]
    )
    job: ApplicationJobHeaderResponse = Field(
        description="Public summary of the associated job.",
        examples=[
            {
                "id": "job-123",
                "title": "Software Engineer",
                "company": "Example Co",
                "location": "Remote",
                "url": "https://example.com/jobs/1",
                "source": "CompanyWebsite",
                "postingDate": "2026-10-01",
            }
        ],
    )


class ApplicationJournalPage(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={"example": {"items": [], "total": 0, "page": 1, "limit": 20, "totalPages": 0}},
    )

    items: list[ApplicationJournalResponse] = Field(description="Page of application entries.", examples=[[]])
    total: int = Field(description="Total matching entries.", examples=[0])
    page: int = Field(description="One-based page number.", examples=[1])
    limit: int = Field(description="Maximum entries requested per page.", examples=[20])
    total_pages: int = Field(serialization_alias="totalPages", description="Number of matching pages.", examples=[0])
