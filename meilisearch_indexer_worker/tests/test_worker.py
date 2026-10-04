"""Unit tests for the Meilisearch indexer worker."""

from unittest.mock import MagicMock

import pytest

from models.data.infrastructure.s3.enums import MetadataType
from meilisearch_indexer_worker.worker import MeilisearchIndexerWorker

REVISION = {
    "revision": {
        "hashes": {
            "labels": {"en": 11},
            "descriptions": {"en": 12},
            "aliases": {"en": [13]},
        }
    },
    "created_at": "2026-01-01T00:00:00Z",
}

TERM_TEXTS = {
    MetadataType.LABELS: {11: "Douglas Adams"},
    MetadataType.DESCRIPTIONS: {12: "English writer"},
    MetadataType.ALIASES: {13: "Douglas Noel Adams"},
}


@pytest.fixture
def worker() -> MeilisearchIndexerWorker:
    """A worker whose database and Meilisearch clients are mocked."""
    worker = MeilisearchIndexerWorker(worker_id="test-indexer")
    worker.db_client = MagicMock()
    worker.db_client.get_head.return_value = 7
    worker.db_client.id_resolver.resolve_id.return_value = 42
    worker.s3_client = MagicMock()
    worker.s3_client.load_metadata.side_effect = lambda metadata_type, content_hash: (
        MagicMock(data=TERM_TEXTS.get(metadata_type, {}).get(content_hash, ""))
    )
    worker.search_client = MagicMock()
    worker.revision_repository = MagicMock()
    worker.revision_repository.get_content_hash.return_value = 555
    worker.revision_data_repository = MagicMock()
    worker.revision_data_repository.load.return_value = REVISION
    return worker


def indexed_ids(worker: MeilisearchIndexerWorker) -> list[str]:
    """Entity IDs that were indexed, in order."""
    return [call.args[0] for call in worker.search_client.index_document.call_args_list]


class TestIndexEntity:
    """Indexing one entity from the database."""

    def test_indexes_the_current_head_revision(
        self, worker: MeilisearchIndexerWorker
    ) -> None:
        """The head revision is used when the event names no revision."""
        assert worker.index_entity("Q42") is True

        document = worker.search_client.index_document.call_args.args[1]
        assert document.id == "Q42"
        assert document.type == "item"
        assert document.lastrevid == 7
        assert document.modified == "2026-01-01T00:00:00Z"
        assert worker.indexed_count == 1

    def test_resolves_the_terms_of_the_revision(
        self, worker: MeilisearchIndexerWorker
    ) -> None:
        """Terms are stored as hashes, so the document holds their text."""
        worker.index_entity("Q42")

        document = worker.search_client.index_document.call_args.args[1]
        assert document.labels == {"en": "Douglas Adams"}
        assert document.descriptions == {"en": "English writer"}
        assert document.aliases == ["Douglas Noel Adams"]
        assert document.label == "Douglas Adams"
        assert document.description == "English writer"

    def test_indexes_the_given_revision(self, worker: MeilisearchIndexerWorker) -> None:
        """A change event carries the revision that changed."""
        assert worker.index_entity("Q42", revision_id=3) is True

        document = worker.search_client.index_document.call_args.args[1]
        assert document.lastrevid == 3
        worker.db_client.get_head.assert_not_called()

    def test_derives_the_type_from_the_id(
        self, worker: MeilisearchIndexerWorker
    ) -> None:
        """Q is an item, P a property, L a lexeme."""
        worker.index_entity("P31")
        assert worker.search_client.index_document.call_args.args[1].type == "property"

        worker.index_entity("L42")
        assert worker.search_client.index_document.call_args.args[1].type == "lexeme"

    def test_skips_entities_without_a_head_revision(
        self, worker: MeilisearchIndexerWorker
    ) -> None:
        """Nothing to index for an entity that was never written."""
        worker.db_client.get_head.return_value = 0

        assert worker.index_entity("Q42") is False
        worker.search_client.index_document.assert_not_called()

    def test_skips_entities_that_no_longer_exist(
        self, worker: MeilisearchIndexerWorker
    ) -> None:
        """An entity that cannot be resolved is not indexed."""
        worker.db_client.id_resolver.resolve_id.return_value = 0

        assert worker.index_entity("Q42") is False
        worker.search_client.index_document.assert_not_called()

    def test_skips_entities_without_revision_data(
        self, worker: MeilisearchIndexerWorker
    ) -> None:
        """A revision that is gone is not indexed."""
        worker.revision_repository.get_content_hash.return_value = 0

        assert worker.index_entity("Q42") is False
        worker.search_client.index_document.assert_not_called()

    def test_skips_entities_whose_revision_data_vanished(
        self, worker: MeilisearchIndexerWorker
    ) -> None:
        """Revision data can disappear between the two reads."""
        worker.revision_data_repository.load.return_value = None

        assert worker.index_entity("Q42") is False
        worker.search_client.index_document.assert_not_called()

    def test_reports_indexing_failures(self, worker: MeilisearchIndexerWorker) -> None:
        """A rejected document is reported, not swallowed."""
        worker.search_client.index_document.return_value = False

        assert worker.index_entity("Q42") is False
        assert worker.indexed_count == 0

    def test_reports_read_failures(self, worker: MeilisearchIndexerWorker) -> None:
        """A database error does not take the worker down."""
        worker.db_client.get_head.side_effect = RuntimeError("db gone")

        assert worker.index_entity("Q42") is False


class TestDeleteEntity:
    """Removing an entity from the index."""

    def test_deletes_the_document(self, worker: MeilisearchIndexerWorker) -> None:
        """The document is removed by entity ID."""
        worker.search_client.delete_document.return_value = True

        assert worker.delete_entity("Q42") is True
        worker.search_client.delete_document.assert_called_once_with("Q42")

    def test_reports_delete_failures(self, worker: MeilisearchIndexerWorker) -> None:
        """A rejected deletion is reported."""
        worker.search_client.delete_document.return_value = False

        assert worker.delete_entity("Q42") is False


class TestProcessMessage:
    """Turning one change event into an index update."""

    async def test_indexes_a_creation(self, worker: MeilisearchIndexerWorker) -> None:
        """A create event indexes the entity."""
        await worker.process_message(
            MagicMock(entity_id="Q42", revision_id=1, change_type="create")
        )

        assert indexed_ids(worker) == ["Q42"]
        worker.search_client.delete_document.assert_not_called()

    async def test_indexes_an_update(self, worker: MeilisearchIndexerWorker) -> None:
        """An update event indexes the new revision."""
        await worker.process_message(
            MagicMock(entity_id="Q42", revision_id=9, change_type="update")
        )

        assert worker.search_client.index_document.call_args.args[1].lastrevid == 9

    @pytest.mark.parametrize("change_type", ["soft_delete", "hard_delete"])
    async def test_removes_a_deletion(
        self, worker: MeilisearchIndexerWorker, change_type: str
    ) -> None:
        """A delete event removes the document instead of indexing it."""
        await worker.process_message(
            MagicMock(entity_id="Q42", revision_id=9, change_type=change_type)
        )

        worker.search_client.delete_document.assert_called_once_with("Q42")
        worker.search_client.index_document.assert_not_called()

    @pytest.mark.parametrize("change_type", ["creation", "edit", "lock"])
    async def test_indexes_other_change_types(
        self, worker: MeilisearchIndexerWorker, change_type: str
    ) -> None:
        """Every change that is not a deletion keeps the entity indexed."""
        await worker.process_message(
            MagicMock(entity_id="Q42", revision_id=9, change_type=change_type)
        )

        assert indexed_ids(worker) == ["Q42"]
        worker.search_client.delete_document.assert_not_called()

    async def test_survives_a_broken_event(
        self, worker: MeilisearchIndexerWorker
    ) -> None:
        """An event that cannot be handled does not raise."""
        await worker.process_message(MagicMock(side_effect=RuntimeError("no entity_id")))

    async def test_skips_events_without_an_entity(
        self, worker: MeilisearchIndexerWorker
    ) -> None:
        """An event without an entity ID is skipped."""
        await worker.process_message(
            MagicMock(entity_id="", revision_id=1, change_type="create")
        )

        worker.search_client.index_document.assert_not_called()
        worker.search_client.delete_document.assert_not_called()


class TestReindexAll:
    """Backfilling the index on startup."""

    async def test_indexes_every_entity_type(
        self, worker: MeilisearchIndexerWorker
    ) -> None:
        """Each type is paged through until it runs out of entities."""
        pages = {
            ("item", 0): ["Q1", "Q2"],
            ("property", 0): ["P1"],
            ("lexeme", 0): ["L1"],
        }
        worker.db_client.list_entities_by_type.side_effect = (
            lambda entity_type, limit, offset: pages.get((entity_type, offset), [])
        )

        assert await worker.reindex_all() == 4
        assert sorted(indexed_ids(worker)) == ["L1", "P1", "Q1", "Q2"]

    async def test_reports_how_many_were_indexed(
        self, worker: MeilisearchIndexerWorker
    ) -> None:
        """Entities that cannot be indexed are left out of the count."""
        worker.db_client.list_entities_by_type.side_effect = (
            lambda entity_type, limit, offset: ["Q1", "Q2"] if offset == 0 else []
        )
        worker.db_client.id_resolver.resolve_id.side_effect = [42, 0]

        assert await worker.reindex_all(batch_size=2) == 1

    async def test_pages_with_the_given_batch_size(
        self, worker: MeilisearchIndexerWorker
    ) -> None:
        """The backfill asks for entities in batches."""
        worker.db_client.list_entities_by_type.side_effect = (
            lambda entity_type, limit, offset: []
        )

        await worker.reindex_all(batch_size=25)

        for entity_type in ["item", "property", "lexeme"]:
            worker.db_client.list_entities_by_type.assert_any_call(
                entity_type, limit=25, offset=0
            )


class TestHealthCheck:
    """The worker's health endpoint."""

    def test_reports_starting_before_it_runs(
        self, worker: MeilisearchIndexerWorker
    ) -> None:
        """A worker that has not started yet is not healthy."""
        response = worker.health_check()

        assert response.status == "starting"
        assert response.worker_id == "test-indexer"

    def test_reports_healthy_while_running(
        self, worker: MeilisearchIndexerWorker
    ) -> None:
        """A running worker is healthy."""
        worker.running = True

        assert worker.health_check().status == "healthy"