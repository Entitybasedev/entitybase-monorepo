"""Response models for authentication."""

from pydantic import BaseModel, Field


class TokenPayload(BaseModel):
    """Claims carried inside a signed auth token."""

    model_config = {"extra": "ignore"}

    user_id: int
    username: str = ""
    exp: int


class AuthResponse(BaseModel):
    """Successful register/login response with a session token."""

    model_config = {"populate_by_name": True}

    token: str = Field(..., description="Signed bearer token")
    user_id: int = Field(..., description="Numeric user ID")
    username: str = Field(..., description="Username")
