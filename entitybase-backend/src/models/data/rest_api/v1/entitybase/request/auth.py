"""Request models for authentication."""

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """Request to register a new user with credentials."""

    model_config = {"extra": "forbid"}

    username: str = Field(..., min_length=1, max_length=100, description="Username")
    password: str = Field(..., min_length=1, max_length=200, description="Password")
    user_id: int = Field(
        default=0,
        ge=0,
        description="Optional numeric user ID (auto-assigned when 0)",
    )


class LoginRequest(BaseModel):
    """Request to log in with username and password."""

    model_config = {"extra": "forbid"}

    username: str = Field(..., min_length=1, max_length=100, description="Username")
    password: str = Field(..., min_length=1, max_length=200, description="Password")
