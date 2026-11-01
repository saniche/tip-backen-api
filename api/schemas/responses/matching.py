from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.common.enums import MatchReportStatus, MatchScoringStatus


class JobMatchingResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "matching-123",
                "job_id": "job-123",
                "score": 82,
                "eligible": True,
                "scoring_status": "scored",
                "breakdown": {"skills": 82},
            }
        },
    )

    id: str = Field(description="Matching result identifier.", examples=["matching-123"])
    job_id: str = Field(description="Compared job identifier.", examples=["job-123"])
    score: int | None = Field(description="Calculated match score, when scorable.", examples=[82])
    eligible: bool = Field(description="Whether mandatory eligibility criteria were satisfied.", examples=[True])
    scoring_status: MatchScoringStatus = Field(
        description="Whether a numeric score was calculated.", examples=["scored"]
    )
    breakdown: dict[str, Any] | None = Field(description="Score contribution details.", examples=[{"skills": 82}])


class MatchResultResponse(JobMatchingResponse):
    model_config = ConfigDict(extra="forbid")

    rank: int | None = Field(default=None, description="Rank within the report.", examples=[1])
    explanation: dict[str, Any] | None = Field(
        default=None,
        description="Structured explanation of the comparison.",
        examples=[{"notes": "Relevant Python experience"}],
    )


class MatchReportSummaryResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "report-123",
                "status": "completed",
                "created_at": "2026-10-23T12:00:00Z",
                "profile_id": "profile-123",
            }
        },
    )

    id: str = Field(description="Match report identifier.", examples=["report-123"])
    status: MatchReportStatus = Field(description="Report completion state.", examples=["completed"])
    created_at: datetime = Field(description="Report creation time.", examples=["2026-10-23T12:00:00Z"])
    profile_id: str | None = Field(description="Profile version used for matching.", examples=["profile-123"])


class MatchReportResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"id": "report-123", "status": "completed", "results": []}},
    )

    id: str = Field(description="Match report identifier.", examples=["report-123"])
    status: MatchReportStatus = Field(description="Report completion state.", examples=["completed"])
    results: list[MatchResultResponse] = Field(description="Ranked job comparison results.", examples=[[]])
