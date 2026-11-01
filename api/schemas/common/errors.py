from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetails(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "code": "RESOURCE_NOT_FOUND",
                "message": "The requested resource was not found.",
                "details": None,
                "request_id": "e8f4a54d-7fb7-482b-9bb4-06a71372dce3",
            }
        },
    )

    code: str = Field(description="Stable machine-readable error code.", examples=["RESOURCE_NOT_FOUND"])
    message: str = Field(
        description="Safe, human-readable explanation.", examples=["The requested resource was not found."]
    )
    details: Any | None = Field(default=None, description="Optional validation or diagnostic details.", examples=[None])
    request_id: str | None = Field(
        default=None,
        description="Request correlation identifier, when available.",
        examples=["e8f4a54d-7fb7-482b-9bb4-06a71372dce3"],
    )


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": "The requested resource was not found.",
                    "details": None,
                    "request_id": "e8f4a54d-7fb7-482b-9bb4-06a71372dce3",
                }
            }
        },
    )

    error: ErrorDetails = Field(
        description="Error payload containing a stable code and safe message.",
        examples=[
            {
                "code": "RESOURCE_NOT_FOUND",
                "message": "The requested resource was not found.",
                "details": None,
                "request_id": "e8f4a54d-7fb7-482b-9bb4-06a71372dce3",
            }
        ],
    )


ApiErrorResponse = ErrorResponse
