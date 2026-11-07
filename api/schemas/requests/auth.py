from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "candidate@example.com", "password": "StrongPass123!"}},
    )

    email: str = Field(description="Account email address.", examples=["candidate@example.com"])
    password: str = Field(description="Account password; never returned by the API.", examples=["StrongPass123!"])


class UserLogin(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"username": "candidate@example.com", "password": "StrongPass123!"}},
    )

    username: str = Field(
        description="Account email address used as the login name.", examples=["candidate@example.com"]
    )
    password: str = Field(description="Account password.", examples=["StrongPass123!"])
