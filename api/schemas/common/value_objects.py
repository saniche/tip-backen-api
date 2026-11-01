from pydantic import BaseModel, ConfigDict, Field


class RecruiterInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": {"name": "Alex Recruiter"}})

    name: str | None = Field(default=None, description="Recruiter name.", examples=["Alex Recruiter"])
    email: str | None = Field(default=None, description="Recruiter email address.", examples=["alex@example.com"])
    phone: str | None = Field(default=None, description="Recruiter phone number.", examples=["+1-555-0100"])
