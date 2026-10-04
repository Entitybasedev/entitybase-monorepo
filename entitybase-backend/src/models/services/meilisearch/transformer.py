"""Meilisearch transformer.

Turns a stored entity revision into the document Meilisearch indexes.
Terms are content-addressed in the database (a revision only holds hashes),
so they are resolved through a caller-supplied loader before indexing.
"""

import logging
from collections.abc import Callable

from pydantic import BaseModel, Field

from models.data.infrastructure.meilisearch import MeilisearchDocument
from models.data.infrastructure.s3.enums import MetadataType

logger = logging.getLogger(__name__)

PREFERRED_LANGUAGE = "en"

# Entity IDs carry their type in the prefix, the same rule the enumeration
# service uses to hand out IDs
PREFIX_TO_TYPE = {"Q": "item", "P": "property", "L": "lexeme"}

# Loads the text of one content-addressed term, or None when it is gone
TermLoader = Callable[[MetadataType, int], str | None]


class EntityTerms(BaseModel):
    """Resolved term texts of one entity."""

    labels: dict[str, str] = Field(default_factory=dict)
    descriptions: dict[str, str] = Field(default_factory=dict)
    aliases: list[str] = Field(default_factory=list)


class RevisionRef(BaseModel):
    """Which entity revision a search document is built from."""

    entity_id: str = Field(..., description="Entity ID, e.g. Q42")
    entity_type: str = Field(..., description="item, property or lexeme")
    lastrevid: int = Field(default=0, description="Revision the document is built from")
    modified: str = Field(default="", description="Revision timestamp (ISO 8601)")


def entity_type_from_id(entity_id: str) -> str:
    """Get the entity type of an ID: Q is an item, P a property, L a lexeme."""
    return PREFIX_TO_TYPE.get(entity_id[:1].upper(), "")


def resolve_terms(hashes: dict, load_term: TermLoader) -> EntityTerms:
    """Resolve the term hashes of a revision into their texts.

    Args:
        hashes: the `hashes` mapping of a revision (labels, descriptions,
            aliases), where each value is a content hash or a list of them.
        load_term: loads the text for one content hash.

    Returns:
        The resolved terms; missing hashes are skipped, not faked.
    """
    labels: dict[str, str] = {}
    descriptions: dict[str, str] = {}
    aliases: list[str] = []

    for language, content_hash in (hashes.get("labels") or {}).items():
        text = _load(load_term, MetadataType.LABELS, content_hash)
        if text:
            labels[language] = text

    for language, content_hash in (hashes.get("descriptions") or {}).items():
        text = _load(load_term, MetadataType.DESCRIPTIONS, content_hash)
        if text:
            descriptions[language] = text

    for alias_hashes in (hashes.get("aliases") or {}).values():
        for content_hash in alias_hashes:
            text = _load(load_term, MetadataType.ALIASES, content_hash)
            if text and text not in aliases:
                aliases.append(text)

    return EntityTerms(labels=labels, descriptions=descriptions, aliases=aliases)


def build_document(
    revision_ref: RevisionRef,
    revision: dict,
    load_term: TermLoader,
) -> MeilisearchDocument:
    """Build the Meilisearch document for one entity revision.

    Args:
        revision_ref: which entity and revision the document is built from.
        revision: the stored revision (its `hashes` hold the term hashes).
        load_term: loads the text for one content hash.

    Returns:
        The document to index.
    """
    terms = resolve_terms(revision.get("hashes") or {}, load_term)

    return MeilisearchDocument(
        id=revision_ref.entity_id,
        type=revision_ref.entity_type,
        lastrevid=revision_ref.lastrevid,
        modified=revision_ref.modified,
        label=_primary_term(terms.labels),
        description=_primary_term(terms.descriptions),
        labels=terms.labels,
        descriptions=terms.descriptions,
        aliases=terms.aliases,
    )


def _load(load_term: TermLoader, metadata_type: MetadataType, content_hash: object) -> str:
    """Load one term text, treating a missing or broken hash as no text."""
    if not isinstance(content_hash, int):
        return ""
    try:
        text = load_term(metadata_type, content_hash)
    except Exception as e:
        logger.warning(f"Could not load {metadata_type.value} {content_hash}: {e}")
        return ""
    return text or ""


def _primary_term(terms_by_language: dict[str, str]) -> str:
    """Pick the term to show for an entity: English, else the first by code."""
    if not terms_by_language:
        return ""
    if PREFERRED_LANGUAGE in terms_by_language:
        return terms_by_language[PREFERRED_LANGUAGE]
    return terms_by_language[sorted(terms_by_language)[0]]