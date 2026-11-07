from pydantic import BaseModel, ConfigDict, Field


class JobNormalizeRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://jobs.example.com/123",
                "content": "Software Engineer role ...",
                "title": "Software Engineer",
                "company": "Example Co",
                "location": "Remote",
            }
        },
    )

    url: str = Field(description="Source URL for the job posting.", examples=["https://jobs.example.com/123"])
    content: str = Field(description="Raw job posting content to normalize.", examples=["Software Engineer role ..."])
    title: str | None = Field(
        default=None, description="Optional title supplied by the client.", examples=["Software Engineer"]
    )
    company: str | None = Field(
        default=None, description="Optional employer name supplied by the client.", examples=["Example Co"]
    )
    location: str | None = Field(
        default=None, description="Optional job location supplied by the client.", examples=["Remote"]
    )
