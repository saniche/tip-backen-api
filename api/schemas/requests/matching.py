from pydantic import BaseModel, ConfigDict, Field


class JobMatchingRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"job_id": "job-123"}})

    job_id: str = Field(
        description="Normalized job identifier to match against the selected profile.", examples=["job-123"]
    )


class MatchCreateRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"job_ids": ["job-123", "job-456"]}})

    job_ids: list[str] = Field(description="One or more normalized job identifiers.", examples=[["job-123", "job-456"]])


class MatchReportRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"job_ids": ["job-123"]}})

    job_ids: list[str] = Field(description="Normalized job identifiers to evaluate.", examples=[["job-123"]])
