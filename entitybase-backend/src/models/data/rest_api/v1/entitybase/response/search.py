"""Search response models."""

from pydantic import BaseModel, Field


class SearchHit(BaseModel):
    """One entity matching a search query."""

    entity_id: str = Field(..., description="Entity ID, e.g. Q42")
    type: str = Field(..., description="item, property or lexeme")
    label: str = Field(default="", description="Label in the default language")
    description: str = Field(default="", description="Description in the default language")
    lastrevid: int = Field(default=0, description="Revision the hit was indexed from")


class SearchResponse(BaseModel):
    """API response for an entity search."""

    query: str = Field(..., description="The search query")
    type: str = Field(
        default="", description="Entity type filter; empty means all types"
    )
    index: str = Field(..., description="Meilisearch index that was searched")
    hits: list[SearchHit] = Field(default_factory=list, description="Matching entities")
    estimated_total_hits: int = Field(
        default=0, description="Estimated number of matching entities"
    )
    limit: int = Field(..., description="Maximum number of hits returned")
    offset: int = Field(..., description="Number of hits skipped")
    processing_time_ms: int = Field(default=0, description="Query time in milliseconds")