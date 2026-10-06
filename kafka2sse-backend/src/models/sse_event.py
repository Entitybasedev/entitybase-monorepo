from typing import Any

from pydantic import BaseModel, Field, field_validator


class SSEEvent(BaseModel):
    """Server-Sent Events message format.

    `data` is the message as it came off the topic, not a model of it. This
    gateway relays several topics whose payloads follow different schemas -
    entity changes, RDF diffs - and those schemas live in other projects, so
    naming one of them here meant every message on any other topic was rejected
    as invalid. That surfaced as a warning and an empty stream rather than as
    an error, which is a poor way to be told.

    Validating here bought nothing: the producer already validated the payload
    before publishing it, and a consumer that wants the shape parses it.
    """

    model_config = {
        "populate_by_name": True,
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
        },
    }

    event_type: str = Field(
        default="entity_change", description="Event type identifier"
    )
    id: str = Field(..., description="Unique ID for SSE event")
    data: dict[str, Any] = Field(..., description="The message, as published")

    @field_validator("data", mode="before")
    @classmethod
    def coerce_data(cls, v: Any) -> Any:
        """Accept a payload model as readily as a plain dict.

        Callers that hold a typed event should not have to dump it by hand, and
        what reaches the wire is a dict either way.
        """
        if isinstance(v, BaseModel):
            return v.model_dump()
        return v