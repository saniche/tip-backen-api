from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.common.enums import ApplicationStatus


class DashboardFollowUpItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Application journal entry identifier.")
    job_title: str = Field(description="Job title.")
    company: str | None = Field(description="Employer name, if available.")
    follow_up_date: date = Field(description="Planned follow-up date.")


class DashboardFollowUps(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int = Field(description="Total due follow-ups, independent of the item limit.")
    items: list[DashboardFollowUpItem] = Field(description="Oldest due follow-ups, ordered by date and application ID.")


class DashboardApplications(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int = Field(description="Total application journal entries.")
    by_status: dict[ApplicationStatus, int] = Field(description="Count for each application status, including zeros.")
    follow_ups_due: DashboardFollowUps


class DashboardTotal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int = Field(description="Total owned records.")


class DashboardSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    applications: DashboardApplications
    interests: DashboardTotal
    matching_reports: DashboardTotal
    tailoring_requests: DashboardTotal
    profiles: DashboardTotal
