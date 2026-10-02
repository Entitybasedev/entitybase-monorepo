"""Response models for user listings."""

from pydantic import BaseModel, Field


class UserListItem(BaseModel):
    """Single user in a user list response."""

    model_config = {"populate_by_name": True}

    user_id: int = Field(..., description="Numeric user ID")
    username: str = Field("", description="Username (empty for users without credentials)")
    created_at: str = Field("", description="Account creation time")
    last_activity: str = Field("", description="Last activity time")


class UserListResponse(BaseModel):
    """Response model for user list queries."""

    model_config = {"populate_by_name": True}

    users: list[UserListItem] = Field(..., description="Page of users")
    count: int = Field(..., description="Number of users on this page")
