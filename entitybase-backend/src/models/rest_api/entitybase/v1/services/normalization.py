"""Turn a stored revision into a normalized entity document.

The revision stores terms, sitelinks and statements as content hashes so
identical content is stored once. That is the right shape for storage and the
wrong shape for a client that wants to read an entity, which would otherwise
have to resolve every hash itself.

The document is Entitybase's own JSON. It is deliberately *not* Wikibase JSON:
Wikibase JSON is an import format we parse on the way in and never emit, so
there is no Wikibase schema here to conform to. The shape is specified in
docs/ARCHITECTURE/ENTITYBASE-JSON.md.

This module resolves those hashes back into the values they stand for, in a
fixed number of queries regardless of how many references the entity has: each
kind of content is collected first, deduplicated, then fetched with a single
batch query. A hash that cannot be resolved is an error rather than a silently
missing value, so a caller never gets a document that looks complete but is not.
"""

import logging
from typing import Any, NoReturn

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
        self._statement_cache: dict[int, dict[str, Any]] = {}
        self._snak_cache: dict[int, dict[str, Any]] = {}
        self._qualifier_cache: dict[int, dict[str, Any]] = {}
        self._reference_cache: dict[int, dict[str, Any]] = {}

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
        """[hash] -> statements with every hash inside them resolved too.

        A stored statement hashes what it shares: its mainsnak, its qualifiers
        and its references are each content-addressed, so resolving the
        statement hash alone still leaves three numbers behind. Those are
        loaded one batch each, so the query count stays fixed per content type
        however many statements the entity has.
        """
        if not hashes:
            return []
        wanted = list(dict.fromkeys(int(h) for h in hashes))
        self._load_statements(wanted)
        statements = [self._stored_statement(h, entity_id) for h in wanted]
        self._load_shared_statement_parts(statements)
        return [self._statement_document(s) for s in statements]

    def _load_statements(self, wanted: list[int]) -> None:
        """Resolve any not-yet-seen statement hashes, in one query."""
        missing = [h for h in wanted if h not in self._statement_cache]
        if missing:
            self._statement_cache.update(self._s3.load_statements_batch(missing))

    def _stored_statement(self, content_hash: int, entity_id: str) -> dict[str, Any]:
        """The stored statement for one hash, or an error naming what is missing."""
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
        return statement

    def _load_shared_statement_parts(self, statements: list[dict[str, Any]]) -> None:
        """Resolve the qualifiers, references and snaks the statements share.

        One batch per content type, in the order their hashes become known:
        qualifiers and references first, since their snak hashes are only
        visible once they are loaded.
        """
        qualifiers = _hashes_of(statements, "qualifiers")
        self._load_qualifiers(qualifiers)
        references = _hashes_in_lists(statements, "references")
        self._load_references(references)

        snaks = _hashes_of(statements, "mainsnak")
        for qualifier in self._picked(self._qualifier_cache, qualifiers):
            snaks.extend(_hashes_of_snak_map(qualifier))
        for reference in self._picked(self._reference_cache, references):
            snaks.extend(_hashes_of_snak_map(reference.get("snaks") or {}))
        self._load_snaks(snaks)

    def _picked(
        self, cache: dict[int, dict[str, Any]], wanted: list[int]
    ) -> list[dict[str, Any]]:
        """The stored objects for these hashes, in the order asked for."""
        return [cache[h] for h in wanted if h in cache]

    def _load_snaks(self, wanted: list[int]) -> None:
        """Resolve any not-yet-seen snak hashes, in one query."""
        missing = [h for h in dict.fromkeys(wanted) if h not in self._snak_cache]
        if missing:
            for content_hash, snak in zip(
                missing, self._s3.load_snaks_batch(missing), strict=True
            ):
                if snak is not None:
                    self._snak_cache[content_hash] = snak.snak

    def _load_qualifiers(self, wanted: list[int]) -> None:
        """Resolve any not-yet-seen qualifier hashes, in one query."""
        missing = [h for h in dict.fromkeys(wanted) if h not in self._qualifier_cache]
        if not missing:
            return
        for content_hash, qualifier in zip(
            missing, self._s3.load_qualifiers_batch(missing), strict=True
        ):
            if qualifier is None:
                self._missing("qualifier", content_hash)
            self._qualifier_cache[content_hash] = qualifier.qualifier

    def _load_references(self, wanted: list[int]) -> None:
        """Resolve any not-yet-seen reference hashes, in one query."""
        missing = [h for h in dict.fromkeys(wanted) if h not in self._reference_cache]
        if not missing:
            return
        for content_hash, reference in zip(
            missing, self._s3.load_references_batch(missing), strict=True
        ):
            if reference is None:
                self._missing("reference", content_hash)
            self._reference_cache[content_hash] = reference.reference

    def _missing(self, kind: str, content_hash: int) -> NoReturn:
        logger.error(
            "Normalization failed: %s hash %s is not stored", kind, content_hash
        )
        raise_validation_error(
            f"Entity could not be normalized: {kind} is missing", status_code=500
        )

    def _statement_document(self, statement: dict[str, Any]) -> dict[str, Any]:
        """One statement with its mainsnak, qualifiers and references resolved."""
        document = dict(statement)

        mainsnak = _hash_value(statement.get("mainsnak"))
        if mainsnak:
            document["mainsnak"] = self._snak(mainsnak)

        qualifiers = _hash_value(statement.get("qualifiers"))
        if qualifiers:
            document["qualifiers"] = self._snak_map(
                self._qualifier_cache[qualifiers]
            )

        references = statement.get("references")
        if isinstance(references, list):
            document["references"] = [
                self._reference_document(self._reference_cache[h])
                for h in dict.fromkeys(_hashes_in(references))
                if h in self._reference_cache
            ]

        return document

    def _reference_document(self, reference: dict[str, Any]) -> dict[str, Any]:
        """One reference with its snaks resolved, keeping its other keys."""
        document = dict(reference)
        snaks = reference.get("snaks")
        if isinstance(snaks, dict):
            document["snaks"] = self._snak_map(snaks)
        return document

    def _snak_map(self, hashes: dict[str, Any]) -> dict[str, Any]:
        """{property: [hash, ...]} -> {property: [snak, ...]}"""
        return {
            prop: [self._snak(h) for h in _hashes_in(values)]
            for prop, values in hashes.items()
            if isinstance(values, list)
        }

    def _snak(self, content_hash: int) -> dict[str, Any]:
        """The snak a hash stands for, or an error naming what is missing."""
        snak = self._snak_cache.get(content_hash)
        if snak is None:
            self._missing("snak", content_hash)
        return snak


def _hash_value(value: Any) -> int:
    """A stored content hash as an int, or 0 if this is not one.

    Hashes travel as numbers, but arrive as digit strings from JSON written by
    other tools, so both count. `bool` is an `int` in Python and never a hash.
    0 is not a hash anything is stored under, so it doubles as "no hash here".
    """
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _hashes_in(values: Any) -> list[int]:
    """Every hash in a value or list of values, in the order they appear."""
    if not isinstance(values, list):
        values = [values]
    return [h for h in (_hash_value(v) for v in values) if h]


def _hashes_of(statements: list[dict[str, Any]], key: str) -> list[int]:
    """Every hash stored under one key of the statements, deduplicated in order."""
    values = [s.get(key) for s in statements]
    return list(dict.fromkeys(h for v in values for h in _hashes_in(v)))


def _hashes_in_lists(statements: list[dict[str, Any]], key: str) -> list[int]:
    """Every hash in the lists stored under one key of the statements."""
    found: list[int] = []
    for statement in statements:
        found.extend(_hashes_in(statement.get(key)))
    return list(dict.fromkeys(found))


def _hashes_of_snak_map(hash_map: dict[str, Any]) -> list[int]:
    """Every snak hash in a {property: [hash, ...]} map."""
    found: list[int] = []
    for values in hash_map.values():
        found.extend(_hashes_in(values))
    return found
