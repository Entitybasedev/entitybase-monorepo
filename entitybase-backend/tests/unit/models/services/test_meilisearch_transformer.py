"""Unit tests for the Meilisearch transformer."""

import pytest

from models.data.infrastructure.s3.enums import MetadataType
from models.services.meilisearch.transformer import (
    RevisionRef,
    build_document,
    entity_type_from_id,
    resolve_terms,
)

TERMS = {
    (MetadataType.LABELS, 11): "Douglas Adams",
    (MetadataType.LABELS, 12): "Douglas Adams",
    (MetadataType.DESCRIPTIONS, 21): "English writer",
    (MetadataType.ALIASES, 31): "Douglas Noel Adams",
    (MetadataType.ALIASES, 32): "Douglas N. Adams",
    (MetadataType.ALIASES, 33): "Douglas Noel Adams",
}


def loader(metadata_type: MetadataType, content_hash: int) -> str | None:
    """Load a term text, like the S3 client does."""
    return TERMS.get((metadata_type, content_hash))


REVISION = {
    "hashes": {
        "labels": {"en": 11, "sv": 12},
        "descriptions": {"en": 21},
        "aliases": {"en": [31, 33], "sv": [32]},
    },
    "state": {"is_locked": False},
}


class TestEntityTypeFromId:
    """Deriving the entity type from an ID."""

    @pytest.mark.parametrize(
        ("entity_id", "expected"),
        [
            ("Q42", "item"),
            ("P31", "property"),
            ("L42", "lexeme"),
            ("E1", ""),
            ("", ""),
        ],
    )
    def test_type_from_prefix(self, entity_id: str, expected: str) -> None:
        """The prefix of an entity ID is its type."""
        assert entity_type_from_id(entity_id) == expected


class TestResolveTerms:
    """Turning the term hashes of a revision into text."""

    def test_resolves_labels_descriptions_and_aliases(self) -> None:
        """Every term hash is replaced by its text."""
        terms = resolve_terms(REVISION["hashes"], loader)

        assert terms.labels == {"en": "Douglas Adams", "sv": "Douglas Adams"}
        assert terms.descriptions == {"en": "English writer"}
        assert terms.aliases == ["Douglas Noel Adams", "Douglas N. Adams"]

    def test_deduplicates_aliases(self) -> None:
        """The same alias in two languages is indexed once."""
        terms = resolve_terms(REVISION["hashes"], loader)

        assert terms.aliases.count("Douglas Noel Adams") == 1

    def test_handles_a_revision_without_terms(self) -> None:
        """An entity without terms resolves to nothing."""
        terms = resolve_terms({}, loader)

        assert terms.labels == {}
        assert terms.descriptions == {}
        assert terms.aliases == []

    def test_skips_hashes_that_no_longer_resolve(self) -> None:
        """A missing hash is skipped rather than faked."""

        def missing(metadata_type: MetadataType, content_hash: int) -> str | None:
            return None

        terms = resolve_terms(REVISION["hashes"], missing)

        assert terms.labels == {}
        assert terms.aliases == []

    def test_survives_a_loader_that_raises(self) -> None:
        """A broken term read does not lose the other terms."""

        def broken(metadata_type: MetadataType, content_hash: int) -> str | None:
            if metadata_type == MetadataType.DESCRIPTIONS:
                raise RuntimeError("storage gone")
            return loader(metadata_type, content_hash)

        terms = resolve_terms(REVISION["hashes"], broken)

        assert terms.labels == {"en": "Douglas Adams", "sv": "Douglas Adams"}
        assert terms.descriptions == {}


class TestBuildDocument:
    """Building the document that goes into the index."""

    def test_builds_a_complete_document(self) -> None:
        """The document carries the searchable terms of the revision."""
        document = build_document(
            RevisionRef(
                entity_id="Q42",
                entity_type="item",
                lastrevid=7,
                modified="2026-01-01T00:00:00Z",
            ),
            REVISION,
            loader,
        )

        assert document.id == "Q42"
        assert document.type == "item"
        assert document.lastrevid == 7
        assert document.modified == "2026-01-01T00:00:00Z"
        assert document.labels == {"en": "Douglas Adams", "sv": "Douglas Adams"}
        assert document.descriptions == {"en": "English writer"}
        assert document.aliases == ["Douglas Noel Adams", "Douglas N. Adams"]

    def test_prefers_english_as_the_primary_label(self) -> None:
        """The label shown for an entity is its English one."""
        document = build_document(
            RevisionRef(entity_id="Q42", entity_type="item"),
            {
                "hashes": {
                    "labels": {"sv": 12, "en": 11},
                    "descriptions": {"sv": 21},
                }
            },
            loader,
        )

        assert document.label == "Douglas Adams"

    def test_falls_back_to_the_first_language(self) -> None:
        """An entity without an English label still gets one."""
        document = build_document(
            RevisionRef(entity_id="Q42", entity_type="item"),
            {"hashes": {"labels": {"sv": 12}}},
            loader,
        )

        assert document.label == "Douglas Adams"

    def test_an_entity_without_terms_is_still_indexable(self) -> None:
        """An entity with no terms yields an empty, valid document."""
        document = build_document(
            RevisionRef(entity_id="Q42", entity_type="item"),
            {"hashes": {}},
            loader,
        )

        assert document.label == ""
        assert document.description == ""
        assert document.aliases == []

    def test_serializes_to_the_indexed_fields(self) -> None:
        """The dumped document is what Meilisearch stores."""
        document = build_document(
            RevisionRef(entity_id="Q42", entity_type="item", lastrevid=7),
            REVISION,
            loader,
        )

        dumped = document.model_dump(mode="json")

        assert dumped["id"] == "Q42"
        assert dumped["type"] == "item"
        assert dumped["lastrevid"] == 7
        assert set(dumped) == {
            "id",
            "type",
            "lastrevid",
            "modified",
            "label",
            "description",
            "labels",
            "descriptions",
            "aliases",
        }