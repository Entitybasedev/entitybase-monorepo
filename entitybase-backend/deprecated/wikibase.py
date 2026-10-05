from typing import Dict, List, Any

from pydantic import BaseModel, Field


class WikibaseEntityResponse(BaseModel):
    """Response model for Wikibase REST API entity endpoints."""

    id: str
    type: str  # "item", "property", "lexeme"
    labels: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    descriptions: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    aliases: Dict[str, List[Dict[str, str]]] = Field(default_factory=dict)
    claims: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    sitelinks: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
