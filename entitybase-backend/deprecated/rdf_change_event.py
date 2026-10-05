from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class RDFChangeEvent(BaseModel):
    """RDF change event following MediaWiki recentchange schema."""

    model_config = ConfigDict(populate_by_name=True)

    # Required fields from schema
    schema_uri: str = Field(
        default="/wikibase/entity_diff/1.0.0",
        alias="$schema",
        description="Schema URI for the event",
    )
    type: str = Field(default="change", description="Event type")
    namespace: int = Field(description="Namespace of the changed entity")
    title: str = Field(description="Title of the changed entity")
    comment: str = Field(description="Edit comment")
    timestamp: int = Field(description="Unix timestamp of the change")
    user: str = Field(description="Username of the editor")
    bot: bool = Field(description="Whether the edit was made by a bot")
    log_id: int = Field(default=0, description="Log ID if applicable")
    log_type: str = Field(default="", description="Log type")
    log_action: str = Field(default="", description="Log action")
    server_url: str = Field(description="Server URL")
    server_name: str = Field(description="Server name")
    server_script_path: str = Field(description="Script path")
    wiki: str = Field(description="Wiki identifier")

    # Optional fields
    id: int = Field(default=0, description="Event ID")
    minor: bool = Field(default=False, description="Minor edit flag")
    patrolled: bool = Field(default=False, description="Patrolled flag")
    length: dict = Field(default_factory=dict, description="Length changes")
    revision: dict = Field(default_factory=dict, description="Revision details")

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: int) -> str:
        """Serialize timestamp to ISO format."""
        return datetime.fromtimestamp(value).isoformat() + "Z"
