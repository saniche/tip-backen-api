from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.common.enums import JobInterestStatus, JobNormalizationStatus, JobStatus


class JobNormalizationResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "job-123",
                "status": "processing",
                "processing_job_id": "processing-123",
                "title": "Software Engineer",
                "url": "https://jobs.example.com/123",
                "created_at": "2026-10-23T12:00:00Z",
            }
        },
    )

    id: str = Field(description="Identifier of the normalized or queued job.", examples=["job-123"])
    status: JobNormalizationStatus = Field(
        description="Whether normalization is queued or the job already exists.", examples=["processing"]
    )
    processing_job_id: str | None = Field(
        default=None,
        description="Processing job identifier when normalization was queued.",
        examples=["processing-123"],
    )
    title: str | None = Field(default=None, description="Known or supplied job title.", examples=["Software Engineer"])
    url: str | None = Field(
        default=None, description="Source job posting URL.", examples=["https://jobs.example.com/123"]
    )
    created_at: datetime | None = Field(
        default=None, description="Job creation time, when available.", examples=["2026-10-23T12:00:00Z"]
    )


class JobSummaryResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "job-123",
                "url": "https://jobs.example.com/123",
                "title": "Software Engineer",
                "company": "Example Co",
                "location": "Remote",
                "created_at": "2026-10-23T12:00:00Z",
            }
        },
    )

    id: str = Field(description="Job identifier.", examples=["job-123"])
    url: str | None = Field(description="Source job posting URL.", examples=["https://jobs.example.com/123"])
    title: str = Field(description="Job title.", examples=["Software Engineer"])
    company: str | None = Field(description="Employer name.", examples=["Example Co"])
    location: str | None = Field(description="Job location.", examples=["Remote"])
    created_at: datetime = Field(description="Job record creation time.", examples=["2026-10-23T12:00:00Z"])


class JobDetailResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "job-123",
                "url": "https://jobs.example.com/123",
                "title": "Software Engineer",
                "company": "Example Co",
                "location": "Remote",
                "salary": "$100,000 CAD",
                "source": "CompanyWebsite",
                "posting_date": "2026-10-01",
                "summary": "Build APIs.",
                "key_responsibilities": ["Build APIs"],
                "requirements": {"qualifications": [], "skills": ["Python"]},
                "desirables": {"qualifications": [], "skills": []},
                "tools_and_technologies": ["Python"],
                "additionals": [],
                "status": "completed",
                "submitter_id": "user-123",
                "created_at": "2026-10-23T12:00:00Z",
                "has_write_access": True,
                "is_interested": False,
                "is_tracked": False,
            }
        },
    )

    id: str = Field(description="Job identifier.", examples=["job-123"])
    url: str | None = Field(description="Source job posting URL.", examples=["https://jobs.example.com/123"])
    title: str = Field(description="Job title.", examples=["Software Engineer"])
    company: str | None = Field(description="Employer name.", examples=["Example Co"])
    location: str | None = Field(description="Job location.", examples=["Remote"])
    salary: str | None = Field(description="Salary information, when available.", examples=["$100,000 CAD"])
    source: str | None = Field(description="Source board or employer.", examples=["CompanyWebsite"])
    posting_date: str | None = Field(description="Source posting date.", examples=["2026-10-01"])
    summary: str | None = Field(description="Normalized job summary.", examples=["Build APIs."])
    key_responsibilities: list[str] = Field(
        description="Key responsibilities from the posting.", examples=[["Build APIs"]]
    )
    requirements: dict[str, Any] | list[Any] = Field(
        description="Required qualifications and skills.", examples=[{"qualifications": [], "skills": ["Python"]}]
    )
    desirables: dict[str, Any] | list[Any] = Field(
        description="Preferred qualifications and skills.", examples=[{"qualifications": [], "skills": []}]
    )
    tools_and_technologies: list[str] = Field(description="Tools and technologies mentioned.", examples=[["Python"]])
    additionals: list[str] = Field(description="Additional job details.", examples=[[]])
    status: JobStatus = Field(description="Job normalization state.", examples=["completed"])
    submitter_id: str | None = Field(
        description="Submitter identifier retained for response compatibility.", examples=["user-123"]
    )
    created_at: datetime = Field(description="Job record creation time.", examples=["2026-10-23T12:00:00Z"])
    has_write_access: bool = Field(description="Whether the current user may modify this job.", examples=[True])
    is_interested: bool = Field(description="Whether the current user saved interest in this job.", examples=[False])
    is_tracked: bool = Field(
        description="Whether this job appears in the current user's application journal.", examples=[False]
    )


class NormalizedJobHeader(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(description="Job identifier.", examples=["job-123"])
    title: str = Field(description="Job title.", examples=["Senior Engineer"])
    company: str | None = Field(description="Employer name.", examples=["Example Co"])
    location: str | None = Field(description="Job location.", examples=["Remote"])
    posting_date: str | None = Field(
        serialization_alias="postingDate", description="Source posting date.", examples=["2026-10-01"]
    )
    source: str | None = Field(description="Source board or employer.", examples=["CompanyWebsite"])


class NormalizedJobsResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid", json_schema_extra={"example": {"items": [], "total": 0, "page": 1, "limit": 20}}
    )

    items: list[NormalizedJobHeader] = Field(description="Page of completed normalized job summaries.", examples=[[]])
    total: int = Field(description="Total matching jobs.", examples=[0])
    page: int = Field(default=1, description="One-based page number.", examples=[1])
    limit: int = Field(default=20, description="Maximum jobs requested per page.", examples=[20])


class InterestJobHeader(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(description="Job identifier.", examples=["job-123"])
    title: str = Field(description="Job title.", examples=["Senior Engineer"])
    company: str | None = Field(description="Employer name.", examples=["Example Co"])
    location: str | None = Field(description="Job location.", examples=["Remote"])
    url: str | None = Field(description="Source posting URL.", examples=["https://jobs.example.com/123"])
    source: str | None = Field(description="Source board or employer.", examples=["CompanyWebsite"])
    posting_date: str | None = Field(
        serialization_alias="postingDate", description="Source posting date.", examples=["2026-10-01"]
    )


class InterestItem(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "interest-123",
                "jobId": "job-123",
                "createdAt": "2026-10-23T12:00:00Z",
                "job": {
                    "id": "job-123",
                    "title": "Senior Engineer",
                    "company": "Example Co",
                    "location": "Remote",
                    "url": "https://jobs.example.com/123",
                    "source": "CompanyWebsite",
                    "postingDate": "2026-10-01",
                },
            }
        },
    )

    id: str = Field(description="Interest record identifier.", examples=["interest-123"])
    job_id: str = Field(serialization_alias="jobId", description="Associated job identifier.", examples=["job-123"])
    created_at: datetime = Field(
        serialization_alias="createdAt", description="When the job was saved.", examples=["2026-10-23T12:00:00Z"]
    )
    job: InterestJobHeader = Field(
        description="Summary of the saved job.", examples=[{"id": "job-123", "title": "Senior Engineer"}]
    )


class InterestsPage(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={"example": {"items": [], "total": 0, "page": 1, "limit": 20, "totalPages": 0}},
    )

    items: list[InterestItem] = Field(description="Page of saved jobs.", examples=[[]])
    total: int = Field(description="Total saved jobs matching the filters.", examples=[0])
    page: int = Field(default=1, description="One-based page number.", examples=[1])
    limit: int = Field(default=20, description="Maximum items requested per page.", examples=[20])
    total_pages: int = Field(serialization_alias="totalPages", description="Number of matching pages.", examples=[0])


class JobInterestResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid", json_schema_extra={"example": {"id": "interest-123", "status": "created"}}
    )

    id: str = Field(description="Interest record identifier.", examples=["interest-123"])
    status: JobInterestStatus = Field(
        description="Whether this request created or reused an interest.", examples=["created"]
    )
