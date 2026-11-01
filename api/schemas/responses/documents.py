from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.common.enums import TailoredDocumentKind


class DefaultDocumentResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "kind": "cv",
                "content": "Experienced software engineer...",
                "filename": "resume.md",
                "created_at": "2026-10-23T12:00:00Z",
                "updated_at": "2026-10-23T12:00:00Z",
            }
        },
    )

    kind: TailoredDocumentKind = Field(description="Stored document category.", examples=["cv"])
    content: str = Field(
        description="Extracted or supplied document text.", examples=["Experienced software engineer..."]
    )
    filename: str | None = Field(description="Original filename, when available.", examples=["resume.md"])
    created_at: datetime = Field(description="Document creation time.", examples=["2026-10-23T12:00:00Z"])
    updated_at: datetime = Field(description="Most recent document update time.", examples=["2026-10-23T12:00:00Z"])
