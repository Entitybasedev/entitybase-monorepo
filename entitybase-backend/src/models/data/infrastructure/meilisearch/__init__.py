"""Meilisearch data models."""

from pydantic import BaseModel, ConfigDict, Field


class MeilisearchDocument(BaseModel):
    """Search document built from one entity revision.

    Terms are stored content-addressed in the database, so the indexer
    resolves them before indexing: `labels` and `descriptions` hold the text
    per language, `aliases` the plain alias strings.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="Entity ID (Q123, P31, L42, ...)")
    type: str = Field(
        ..., description="Entity type: item, property or lexeme"
    )
    lastrevid: int = Field(default=0, description="Revision this document was built from")
    modified: str = Field(default="", description="Revision timestamp (ISO 8601)")
    label: str = Field(default="", description="Label in the chain's default language")
    description: str = Field(
        default="", description="Description in the chain's default language"
    )
    labels: dict[str, str] = Field(
        default_factory=dict, description="Labels by language code"
    )
    descriptions: dict[str, str] = Field(
        default_factory=dict, description="Descriptions by language code"
    )
    aliases: list[str] = Field(
        default_factory=list, description="Alias strings across all languages"
    )


class MeilisearchDocumentResponse(BaseModel):
    """Response model for a Meilisearch document lookup or preview."""

    model_config = ConfigDict(populate_by_name=True)

    data: MeilisearchDocument | None = Field(
        default=None, description="The document, or null when not indexed"
    )
    index: str = Field(default="", description="Index the document lives in")