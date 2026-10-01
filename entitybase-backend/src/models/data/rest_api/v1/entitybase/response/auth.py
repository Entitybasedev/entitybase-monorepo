"""Response models for authentication."""

from pydantic import BaseModel, Field


class AuthResponse(BaseModel):
    """Successful register/login response with a session token."""

    model_config = {"populate_by_name": True}

    token: str = Field(..., description="Signed bearer token")
    user_id: int = Field(..., description="Numeric user ID")
    username: str = Field(..., description="Username")
