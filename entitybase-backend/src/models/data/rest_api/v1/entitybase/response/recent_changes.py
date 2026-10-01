"""Response models for the recent-changes list."""

from pydantic import BaseModel, Field


class RecentChangeEntry(BaseModel):
    """One entry in the recent changes list."""

    model_config = {"populate_by_name": True}

    id: int = Field(..., description="Activity record ID (ordering key)")
    created_at: str = Field(..., description="When the change happened")
    user_id: int = Field(..., description="User who made the change")
    activity_type: str = Field(
        "", description="Coarse activity type (entity_create, entity_edit, ...)"
    )
    change_type: str = Field(
        "",
        description="Granular change type (label_update, statement_add, ...)",
    )
    entity_id: str = Field("", description="Affected entity (e.g. Q42)")
    revision_id: int = Field(0, description="Revision created by the change")
    edit_summary: str = Field("", description="Edit summary supplied by the user")
