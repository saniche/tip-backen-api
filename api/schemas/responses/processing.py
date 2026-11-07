from pydantic import BaseModel, ConfigDict, Field

from api.schemas.common.enums import ProcessingJobStatus


class ProcessingJobResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "processing-123",
                "status": "pending",
                "result_id": None,
                "error": None,
            }
        },
    )

    id: str = Field(description="Identifier used to poll processing status.", examples=["processing-123"])
    status: ProcessingJobStatus = Field(description="Current processing state.", examples=["pending"])
    result_id: str | None = Field(
        default=None, description="Identifier of the completed result, when available.", examples=["result-123"]
    )
    error: str | None = Field(
        default=None, description="Safe failure message, when processing failed.", examples=[None]
    )
