from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid")

    items: list[T] = Field(description="Items on this page.", examples=[[]])
    total: int = Field(description="Total matching items.", examples=[0])
    page: int = Field(default=1, description="One-based page number.", examples=[1])
    limit: int = Field(default=50, description="Maximum items requested per page.", examples=[50])
