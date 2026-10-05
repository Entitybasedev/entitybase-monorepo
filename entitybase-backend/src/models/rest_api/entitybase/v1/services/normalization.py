"""Turn a stored revision into a normalized entity document.

The revision stores terms, sitelinks and statements as content hashes so
identical content is stored once. That is the right shape for storage and the
wrong shape for a client that wants to read an entity, which would otherwise
have to resolve every hash itself.

This module resolves those hashes back into the values they stand for, in a
fixed number of queries regardless of how many references the entity has: each
kind of content is collected first, deduplicated, then fetched with a single
batch query. A hash that cannot be resolved is an error rather than a silently
missing value, so a caller never gets a document that looks complete but is not.
"""

import logging
from typing import Any

from models.data.infrastructure.s3.enums import MetadataType
from models.rest_api.utils import raise_validation_error

logger = logging.getLogger(__name__)

# Terms live in one table per content type, so each needs its own batch query.
TERM_METADATA_TYPES = {
    "labels": MetadataType.LABELS,
    "descriptions": MetadataType.DESCRIPTIONS,
    "aliases": MetadataType.ALIASES,
}


class EntityNormalizer:
    """Builds a normalized document from a stored revision.

    One instance normalizes one entity, so resolved content is reused across
    every place the same hash appears - two labels with the same text, or the
    same statement on two entities' shared subobjects, resolve once.
    """

    def __init__(self, s3_client: Any) -> None:
        self._s3 = s3_client
        # content hash -> resolved text, per content type
        self._term_cache: dict[MetadataType, dict[int, str]] = {}
        self._sitelink_cache: dict[int, str] = {}
        self._statement_cache: dict[int, Any] = {}

    def normalize(self, entity_id: str, revision: dict[str, Any]) -> dict[str, Any]:
        """Return the revision with every hash reference resolved to its value.

        The `hashes` block is dropped: it is the internal index, and keeping it
        would leak the storage model this endpoint exists to hide.
        """
        document = {k: v for k, v in revision.items() if k != "hashes"}
        hashes = revision.get("hashes") or {}

        document["labels"] = self._resolve_single_terms(
            "labels", hashes.get("labels") or {}
        )
        document["descriptions"] = self._resolve_single_terms(
            "descriptions", hashes.get("descriptions") or {}
        )
        document["aliases"] = self._resolve_aliases(hashes.get("aliases") or {})
        document["sitelinks"] = self._resolve_sitelinks(hashes.get("sitelinks") or {})
        document["statements"] = self._resolve_statements(
            entity_id, hashes.get("statements") or []
        )
        document["id"] = entity_id
        return document

    def _load_terms(self, metadata_type: MetadataType, wanted: list[int]) -> None:
        """Resolve any not-yet-seen hashes of one content type, in one query."""
        cached = self._term_cache.setdefault(metadata_type, {})
        missing = [h for h in dict.fromkeys(wanted) if h not in cached]
        if missing:
            cached.update(self._s3.load_metadata_batch(metadata_type, missing))

    def _term(self, metadata_type: MetadataType, content_hash: int, kind: str) -> str:
        """The text a term hash stands for, or an error naming what is missing."""
        value = self._term_cache.get(metadata_type, {}).get(content_hash)
        if value is None:
            logger.error(
                "Normalization failed: %s hash %s is not stored", kind, content_hash
            )
            raise_validation_error(
                f"Entity could not be normalized: {kind} is missing", status_code=500
            )
        return value

    def _resolve_single_terms(
        self, kind: str, hashes_by_language: dict[str, Any]
    ) -> dict[str, Any]:
        """{language: hash} -> {language: {language, value}} for one term kind.

        Labels and descriptions share this shape and differ only in which
        content type their hashes live in.
        """
        if not hashes_by_language:
            return {}
        metadata_type = TERM_METADATA_TYPES[kind]
        self._load_terms(metadata_type, [int(h) for h in hashes_by_language.values()])
        return {
            language: {
                "language": language,
                "value": self._term(metadata_type, int(h), kind),
            }
            for language, h in hashes_by_language.items()
        }

    def _resolve_aliases(self, hashes_by_language: dict[str, Any]) -> dict[str, Any]:
        """{language: [hash]} -> {language: [{language, value}]}"""
        if not hashes_by_language:
            return {}
        metadata_type = TERM_METADATA_TYPES["aliases"]
        self._load_terms(
            metadata_type,
            [int(h) for hashes in hashes_by_language.values() for h in hashes],
        )
        return {
            language: [
                {"language": language, "value": self._term(metadata_type, int(h), "alias")}
                for h in hashes
            ]
            for language, hashes in hashes_by_language.items()
        }

    def _resolve_sitelinks(self, hashes_by_site: dict[str, Any]) -> dict[str, Any]:
        """{site: {title_hash, badges}} -> {site: {site, title, badges}}"""
        if not hashes_by_site:
            return {}
        wanted = [int(entry["title_hash"]) for entry in hashes_by_site.values()]
        missing = [h for h in dict.fromkeys(wanted) if h not in self._sitelink_cache]
        if missing:
            self._sitelink_cache.update(self._s3.load_sitelinks_batch(missing))

        resolved: dict[str, Any] = {}
        for site, entry in hashes_by_site.items():
            title_hash = int(entry["title_hash"])
            title = self._sitelink_cache.get(title_hash)
            if title is None:
                logger.error(
                    "Normalization failed: sitelink title hash %s is not stored",
                    title_hash,
                )
                raise_validation_error(
                    "Entity could not be normalized: sitelink title is missing",
                    status_code=500,
                )
            resolved[site] = {
                "site": site,
                "title": title,
                "badges": list(entry.get("badges") or []),
            }
        return resolved

    def _resolve_statements(self, entity_id: str, hashes: list[Any]) -> list[Any]:
        """[hash] -> the stored statement objects, in revision order.

        A statement is stored as its own Wikibase-shaped object, so resolving
        the hash is the whole job; nothing inside it is hashed.
        """
        if not hashes:
            return []
        wanted = [int(h) for h in hashes]
        missing = [h for h in dict.fromkeys(wanted) if h not in self._statement_cache]
        if missing:
            self._statement_cache.update(self._s3.load_statements_batch(missing))

        resolved = []
        for content_hash in wanted:
            statement = self._statement_cache.get(content_hash)
            if statement is None:
                logger.error(
                    "Normalization failed: statement hash %s of %s is not stored",
                    content_hash,
                    entity_id,
                )
                raise_validation_error(
                    "Entity could not be normalized: statement is missing",
                    status_code=500,
                )
            resolved.append(statement)
        return resolved