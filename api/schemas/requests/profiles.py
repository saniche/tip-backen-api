from pydantic import BaseModel, ConfigDict, Field


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"data": {"summary": "Python engineer"}, "output_language": "English"}},
    )

    data: dict = Field(
        description="Profile data to save.", examples=[{"summary": "Python engineer", "skills": ["Python"]}]
    )
    output_language: str = Field(
        default="English", description="Language used for profile content.", examples=["English"]
    )
    label: str | None = Field(
        default=None, max_length=100, description="Optional display label.", examples=["Engineering profile"]
    )


class ProfileSessionCreate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"output_language": "French"}})

    output_language: str = Field(
        default="English", description="Language used to extract and merge profile content.", examples=["French"]
    )


class ProfilePatch(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"data": {"summary": "Updated summary"}, "label": "Engineering profile"}},
    )

    data: dict | None = Field(
        default=None,
        description="Profile fields to update; omitted fields remain unchanged.",
        examples=[{"summary": "Updated summary"}],
    )
    output_language: str | None = Field(
        default=None, description="Updated profile output language.", examples=["English"]
    )
    label: str | None = Field(
        default=None, max_length=100, description="Optional display label.", examples=["Engineering profile"]
    )
