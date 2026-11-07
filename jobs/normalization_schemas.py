from pydantic import BaseModel, ConfigDict, Field


class JobRequirements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    qualifications: list[str] = Field(description="Required qualifications.")
    skills: list[str] = Field(description="Required skills.")


class JobListing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="Job title.")
    posting_date: str | None = Field(description="Source posting date.")
    company: str | None = Field(description="Employer name.")
    location: str | None = Field(description="Job location.")
    salary: str | None = Field(description="Salary information.")
    url: str | None = Field(description="Source posting URL.")
    source: str | None = Field(description="Source board or employer.")
    summary: str | None = Field(description="Job summary.")
    key_responsibilities: list[str] = Field(description="Key responsibilities.")
    required: JobRequirements = Field(description="Required qualifications and skills.")
    desirable: JobRequirements = Field(description="Preferred qualifications and skills.")
    tools_and_technologies: list[str] = Field(description="Tools and technologies.")


class JobExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: list[JobListing] = Field(description="Extracted job postings.")
