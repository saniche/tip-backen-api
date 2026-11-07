from pydantic import BaseModel, ConfigDict, Field


class AuthTokenResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"access_token": "eyJ...redacted", "token_type": "bearer"}},
    )

    access_token: str = Field(description="Signed bearer access token.", examples=["eyJ...redacted"])
    token_type: str = Field(
        default="bearer", description="Authorization scheme for the returned token.", examples=["bearer"]
    )
