from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": {"status": "ok"}})

    status: str = Field(description="Service health state.", examples=["ok"])


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": {"status": "ready"}})

    status: str = Field(description="Dependency readiness state.", examples=["ready"])
