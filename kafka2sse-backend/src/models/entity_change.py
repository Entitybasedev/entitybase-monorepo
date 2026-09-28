from enum import Enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ChangeType(str, Enum):
    """Enumeration of possible entity change types."""
    CREATION = "creation"
    EDIT = "edit"
    REDIRECT = "redirect"
    UNREDIRECT = "unredirect"
    ARCHIVAL = "archival"
    UNARCHIVAL = "unarchival"
    LOCK = "lock"
    UNLOCK = "unlock"
    SOFT_DELETE = "soft_delete"
    HARD_DELETE = "hard_delete"


class EntityChange(BaseModel):
    """Entity change event consumed from Kafka."""

    model_config = ConfigDict(populate_by_name=True)

    entity_id: str = Field(alias="id", description="The ID of the entity that changed")
    revision_id: int = Field(alias="rev", ge=1, description="The new revision ID after the change")
    change_type: ChangeType = Field(alias="type", description="The type of change")
    from_revision_id: Optional[int] = Field(default=0, alias="from_rev", description="The previous revision ID")
    changed_at: str = Field(alias="at", description="Timestamp of the change in ISO 8601 format")
    edit_summary: str = Field(default="", alias="summary", description="Summary of the edit")
    user_id: str = Field(alias="user", description="ID of the user who made the change")

    @field_serializer("changed_at")
    def serialize_changed_at(self, value: datetime) -> str:
        """Serialize datetime to ISO format string."""
        if isinstance(value, datetime):
            return value.isoformat() + "Z"
        return str(value)
