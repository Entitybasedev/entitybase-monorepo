from pydantic import BaseModel, Field, field_validator

from src.models.entity_change import EntityChange


class SSEEvent(BaseModel):
    """Server-Sed Events message format for entity changes."""
    
    model_config = {"populate_by_name": True}
    
    event_type: str = Field(default="entity_change", description="Event type identifier")
    id: str = Field(..., description="Unique ID for SSE event")
    data: EntityChange = Field(..., description="The entity change data")

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if v != "entity_change":
            raise ValueError("event_type must be 'entity_change'")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "event_type": "entity_change",
                    "id": "82c5a9",
                    "data": {
                        "entity_id": "Q42",
                        "revision_id": 12345,
                        "change_type": "edit",
                        "from_revision_id": 12344,
                        "changed_at": "2023-01-01T12:00:00Z",
                        "edit_summary": "Updated description",
                    },
                }
            ]
        }
    }
