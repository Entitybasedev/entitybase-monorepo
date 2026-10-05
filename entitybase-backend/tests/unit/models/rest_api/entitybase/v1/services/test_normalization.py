"""Unit tests for EntityNormalizer."""

from typing import Any

import pytest
from fastapi import HTTPException

from models.data.infrastructure.s3.enums import MetadataType
from models.rest_api.entitybase.v1.services.normalization import EntityNormalizer


class FakeS3:
    """Stands in for the storage client, counting how it is asked for things."""

    def __init__(
        self,
        terms: dict[MetadataType, dict[int, str]] | None = None,
        sitelinks: dict[int, str] | None = None,
        statements: dict[int, Any] | None = None,
    ) -> None:
        self.terms = terms or {}
        self.sitelinks = sitelinks or {}
        self.statements = statements or {}
        self.term_calls: list[tuple[MetadataType, list[int]]] = []
        self.sitelink_calls: list[list[int]] = []
        self.statement_calls: list[list[int]] = []

    def load_metadata_batch(
        self, metadata_type: MetadataType, content_hashes: list[int]
    ) -> dict[int, str]:
        self.term_calls.append((metadata_type, list(content_hashes)))
        stored = self.terms.get(metadata_type, {})
        return {h: stored[h] for h in content_hashes if h in stored}

    def load_sitelinks_batch(self, content_hashes: list[int]) -> dict[int, str]:
        self.sitelink_calls.append(list(content_hashes))
        return {h: self.sitelinks[h] for h in content_hashes if h in self.sitelinks}

    def load_statements_batch(self, content_hashes: list[int]) -> dict[int, Any]:
        self.statement_calls.append(list(content_hashes))
        return {h: self.statements[h] for h in content_hashes if h in self.statements}


def test_resolves_terms_sitelinks_and_statements() -> None:
    """Every hash reference becomes the value it stands for."""
    s3 = FakeS3(
        terms={
            MetadataType.LABELS: {10: "Douglas Adams"},
            MetadataType.DESCRIPTIONS: {20: "English author"},
            MetadataType.ALIASES: {30: "Douglas Noel Adams"},
        },
        sitelinks={40: "Douglas Adams"},
        statements={
            50: {
                "mainsnak": {
                    "snaktype": "value",
                    "property": "P31",
                    "datavalue": {"value": {"id": "Q5"}, "type": "wikibase-item"},
                },
                "type": "statement",
                "rank": "normal",
                "qualifiers": {},
                "references": [],
            }
        },
    )
    revision: dict[str, Any] = {
        "revision_id": 3,
        "entity_type": "item",
        "datatype": "",
        "hashes": {
            "labels": {"en": 10},
            "descriptions": {"en": 20},
            "aliases": {"en": [30]},
            "sitelinks": {"enwiki": {"title_hash": 40, "badges": ["featuredarticle"]}},
            "statements": [50],
        },
    }

    document = EntityNormalizer(s3).normalize("Q42", revision)

    assert document["id"] == "Q42"
    assert document["labels"] == {"en": {"language": "en", "value": "Douglas Adams"}}
    assert document["descriptions"] == {
        "en": {"language": "en", "value": "English author"}
    }
    assert document["aliases"] == {
        "en": [{"language": "en", "value": "Douglas Noel Adams"}]
    }
    assert document["sitelinks"] == {
        "enwiki": {
            "site": "enwiki",
            "title": "Douglas Adams",
            "badges": ["featuredarticle"],
        }
    }
    assert document["statements"] == [s3.statements[50]]


def test_does_not_expose_hashes() -> None:
    """The internal index is dropped, so no content hash reaches the client."""
    s3 = FakeS3(terms={MetadataType.LABELS: {10: "Douglas Adams"}})
    revision: dict[str, Any] = {
        "revision_id": 3,
        "hashes": {"labels": {"en": 10}},
    }

    document = EntityNormalizer(s3).normalize("Q42", revision)

    assert "hashes" not in document
    # 10 is the label's content hash; it must appear nowhere in the output
    assert "10" not in str(document)


def test_queries_each_content_type_once() -> None:
    """Resolution costs one query per content type, not one per reference."""
    s3 = FakeS3(
        terms={
            MetadataType.LABELS: {10: "one", 11: "two", 12: "three"},
            MetadataType.ALIASES: {30: "alias one", 31: "alias two"},
        },
        sitelinks={40: "A", 41: "B"},
        statements={50: {"type": "statement"}, 51: {"type": "statement"}},
    )
    revision: dict[str, Any] = {
        "hashes": {
            "labels": {"en": 10, "sv": 11, "da": 12},
            "aliases": {"en": [30, 31]},
            "sitelinks": {
                "enwiki": {"title_hash": 40, "badges": []},
                "svwiki": {"title_hash": 41, "badges": []},
            },
            "statements": [50, 51],
        }
    }

    EntityNormalizer(s3).normalize("Q42", revision)

    assert [call[0] for call in s3.term_calls] == [
        MetadataType.LABELS,
        MetadataType.ALIASES,
    ]
    assert len(s3.sitelink_calls) == 1
    assert len(s3.statement_calls) == 1


def test_repeated_hash_is_resolved_once() -> None:
    """Two references to the same content share one lookup."""
    s3 = FakeS3(terms={MetadataType.LABELS: {10: "shared"}})
    revision: dict[str, Any] = {
        "hashes": {"labels": {"en": 10, "sv": 10, "da": 10}}
    }

    EntityNormalizer(s3).normalize("Q42", revision)

    assert s3.term_calls == [(MetadataType.LABELS, [10])]


def test_missing_term_is_an_error() -> None:
    """A hash with no stored term fails loudly instead of yielding a blank."""
    s3 = FakeS3()
    revision: dict[str, Any] = {"hashes": {"labels": {"en": 999}}}

    with pytest.raises(HTTPException) as excinfo:
        EntityNormalizer(s3).normalize("Q42", revision)

    assert excinfo.value.status_code == 500
    assert "could not be normalized" in str(excinfo.value.detail)


def test_missing_sitelink_title_is_an_error() -> None:
    """A sitelink whose title is not stored fails loudly."""
    s3 = FakeS3()
    revision: dict[str, Any] = {
        "hashes": {"sitelinks": {"enwiki": {"title_hash": 999, "badges": []}}}
    }

    with pytest.raises(HTTPException) as excinfo:
        EntityNormalizer(s3).normalize("Q42", revision)

    assert excinfo.value.status_code == 500


def test_missing_statement_is_an_error() -> None:
    """A statement hash with nothing stored fails loudly."""
    s3 = FakeS3()
    revision: dict[str, Any] = {"hashes": {"statements": [999]}}

    with pytest.raises(HTTPException) as excinfo:
        EntityNormalizer(s3).normalize("Q42", revision)

    assert excinfo.value.status_code == 500


def test_empty_revision_normalizes_to_empty_collections() -> None:
    """An entity with nothing stored comes back with empty collections, no errors."""
    document = EntityNormalizer(FakeS3()).normalize("Q42", {"hashes": {}})

    assert document["labels"] == {}
    assert document["descriptions"] == {}
    assert document["aliases"] == {}
    assert document["sitelinks"] == {}
    assert document["statements"] == []


def test_keeps_non_hash_revision_fields() -> None:
    """Fields that are not hash references pass through untouched."""
    s3 = FakeS3()
    revision: dict[str, Any] = {
        "revision_id": 7,
        "entity_type": "property",
        "datatype": "string",
        "properties": ["P31"],
        "lemmas": {},
        "hashes": {},
    }

    document = EntityNormalizer(s3).normalize("P42", revision)

    assert document["revision_id"] == 7
    assert document["entity_type"] == "property"
    assert document["datatype"] == "string"
    assert document["properties"] == ["P31"]