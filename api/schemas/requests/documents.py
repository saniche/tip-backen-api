from pydantic import BaseModel, ConfigDict, Field, field_validator

from shared.limits import MAX_DEFAULT_DOCUMENT_CHARS


class DefaultDocumentIn(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"content": "Experienced software engineer...", "filename": "resume.md"}},
    )

    content: str = Field(
        max_length=MAX_DEFAULT_DOCUMENT_CHARS,
        description="Document text content.",
        examples=["Experienced software engineer..."],
    )
    filename: str | None = Field(
        default=None, max_length=200, description="Optional original filename.", examples=["resume.md"]
    )

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be empty")
        return value
