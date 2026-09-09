from pydantic import BaseModel, ConfigDict


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
    matching_id: str
    output_language: str = "English"


class CvTailoringOut(BaseModel):
    id: str
    matching_id: str
    download_url: str
