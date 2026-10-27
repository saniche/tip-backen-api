from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from shared.models import ApplicationStatus


class ErrorDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    details: dict | None = None
    request_id: str | None = None


class ApiErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error: ErrorDetails


class PaginatedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list
    total: int
    page: int = 1
    limit: int = 50


class NormalizedJobHeader(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    title: str
    company: str | None
    location: str | None
    posting_date: str | None = Field(serialization_alias="postingDate")
    source: str | None


class NormalizedJobsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[NormalizedJobHeader]
    total: int
    page: int = 1
    limit: int = 20


class InterestJobHeader(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    title: str
    company: str | None
    location: str | None
    url: str | None
    source: str | None
    posting_date: str | None = Field(serialization_alias="postingDate")


class InterestItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    job_id: str = Field(serialization_alias="jobId")
    created_at: datetime = Field(serialization_alias="createdAt")
    job: InterestJobHeader


class InterestsPage(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    items: list[InterestItem]
    total: int
    page: int = 1
    limit: int = 20
    total_pages: int = Field(serialization_alias="totalPages")


class RecruiterInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    email: str | None = None
    phone: str | None = None


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    job_id: str = Field(validation_alias="jobId", serialization_alias="jobId")
    recruiter_info: RecruiterInfo | None = Field(default=None, validation_alias="recruiterInfo")
    contact_date: date | None = Field(default=None, validation_alias="contactDate")
    follow_up_date: date | None = Field(default=None, validation_alias="followUpDate")
    work_authorization_discussed: bool = Field(default=False, validation_alias="workAuthorizationDiscussed")
    notes: str | None = None


class ApplicationFieldsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    recruiter_info: RecruiterInfo | None = Field(default=None, validation_alias="recruiterInfo")
    contact_date: date | None = Field(default=None, validation_alias="contactDate")
    follow_up_date: date | None = Field(default=None, validation_alias="followUpDate")
    work_authorization_discussed: bool = Field(default=False, validation_alias="workAuthorizationDiscussed")
    notes: str | None = None

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("At least one editable field must be provided")
        return self


class ApplicationStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ApplicationStatus
    note: str | None = None


class ApplicationStatusHistoryOut(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    date: datetime
    note: str | None
    status: ApplicationStatus


class ApplicationJobHeader(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    title: str
    company: str | None
    location: str | None
    url: str | None
    source: str | None
    posting_date: str | None = Field(serialization_alias="postingDate")


class ApplicationJournalItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    job_id: str = Field(serialization_alias="jobId")
    recruiter_info: RecruiterInfo | None = Field(serialization_alias="recruiterInfo")
    contact_date: date | None = Field(serialization_alias="contactDate")
    follow_up_date: date | None = Field(serialization_alias="followUpDate")
    work_authorization_discussed: bool = Field(serialization_alias="workAuthorizationDiscussed")
    notes: str | None
    status: ApplicationStatus
    history: list[ApplicationStatusHistoryOut]
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")
    job: ApplicationJobHeader


class ApplicationJournalPage(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    items: list[ApplicationJournalItem]
    total: int
    page: int
    limit: int
    total_pages: int = Field(serialization_alias="totalPages")


class JobRequirements(BaseModel):
    model_config = ConfigDict(extra="forbid")
    qualifications: list[str]
    skills: list[str]


class JobListing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    posting_date: str | None
    company: str | None
    location: str | None
    salary: str | None
    url: str | None
    source: str | None
    summary: str | None
    key_responsibilities: list[str]
    required: JobRequirements
    desirable: JobRequirements
    tools_and_technologies: list[str]


class JobExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jobs: list[JobListing]


class JobNormalizeRequest(BaseModel):
    url: str
    content: str
    title: str | None = None
    company: str | None = None
    location: str | None = None


class JobNormalizeOut(BaseModel):
    id: str
    status: str
    processing_job_id: str | None = None
    title: str | None = None
    url: str | None = None
    created_at: object | None = None


# --- Auth ---


class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Processing job status (for the backgrounded endpoints) ---


class ProcessingJobOut(BaseModel):
    id: str
    status: str
    result_id: str | None = None
    error: str | None = None


# --- Job matching ---


class JobMatchingRequest(BaseModel):
    job_id: str


class JobMatchingOut(BaseModel):
    id: str
    job_id: str
    score: int | None
    eligible: bool
    scoring_status: str
    breakdown: dict | None = None


class MatchReportRequest(BaseModel):
    job_ids: list[str]


class MatchResultOut(JobMatchingOut):
    rank: int | None = None
    explanation: dict | None = None


class MatchReportOut(BaseModel):
    id: str
    status: str
    results: list[MatchResultOut]


# --- CV tailoring ---


class CvTailoringRequest(BaseModel):
    matching_id: str | None = None
    matching_ids: list[str] = Field(default_factory=list)
    mode: str = "per_job"
    output_language: str = "English"

    @model_validator(mode="after")
    def validate_selection(self):
        if self.matching_id and not self.matching_ids:
            self.matching_ids = [self.matching_id]
        if not self.matching_ids:
            raise ValueError("At least one matching result is required")
        if self.mode not in {"per_job", "group_all"}:
            raise ValueError("mode must be per_job or group_all")
        return self


class CvTailoringOut(BaseModel):
    id: str
    matching_id: str
    download_url: str


class CvMetadataOut(BaseModel):
    id: str
    request_id: str | None = None
    matching_id: str
    mode: str
    status: str
    target_job_ids: list[str]
    download_url: str
