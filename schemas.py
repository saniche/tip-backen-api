from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    technical_stack: list[str]


class JobExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jobs: list[JobListing]


# --- Auth ---


class UserCreate(BaseModel):
    email: str
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
    score: int
    eligible: bool
    scoring_status: str
    breakdown: dict | None = None


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
