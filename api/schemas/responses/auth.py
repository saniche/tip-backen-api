from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "4f9c1f0e-2b7a-4b8e-9d55-0c6c1d2a9e11",
                "email": "candidate@example.com",
                "email_verified": True,
                "username": "candidate@example.com",
                "first_name": "Dev",
                "last_name": "Candidate",
                "role": "user",
                "created_at": "2026-11-23T10:00:00Z",
                "last_login_at": "2026-11-23T10:00:00Z",
            }
        },
    )

    id: str = Field(description="Internal user id used by every owned resource.")
    email: str = Field(description="Email address synced from Keycloak.")
    email_verified: bool = Field(description="Whether Keycloak has verified the email address.")
    username: str | None = Field(default=None, description="Keycloak preferred username.")
    first_name: str | None = Field(default=None, description="Given name from Keycloak.")
    last_name: str | None = Field(default=None, description="Family name from Keycloak.")
    role: Literal["user", "admin"] = Field(description="Platform role mapped from Keycloak roles.")
    created_at: datetime = Field(description="When the local user record was first created.")
    last_login_at: datetime | None = Field(default=None, description="Last time an access token was seen.")
