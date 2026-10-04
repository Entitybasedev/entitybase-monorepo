"""Unit tests for the Meilisearch client."""

from unittest.mock import MagicMock, patch

import pytest

from models.data.infrastructure.meilisearch import MeilisearchDocument
from models.services.meilisearch.client import (
    FILTERABLE_ATTRIBUTES,
    PRIMARY_KEY,
    SEARCHABLE_ATTRIBUTES,
    MeilisearchClient,
)


@pytest.fixture
def client() -> MeilisearchClient:
    """A connected client whose Meilisearch index is mocked."""
    client = MeilisearchClient(host="meilisearch", port=7700, index_name="entitybase")
    client.client = MagicMock()
    # Indexing is asynchronous, so every write ends in a task
    client.client.get_task.return_value = MagicMock(status="succeeded", error=None)
    client.index = MagicMock()
    return client


def document(entity_id: str = "Q42") -> MeilisearchDocument:
    """A document as the indexer would build it."""
    return MeilisearchDocument(
        id=entity_id,
        type="item",
        lastrevid=7,
        label="Douglas Adams",
        description="English writer",
        labels={"en": "Douglas Adams"},
        descriptions={"en": "English writer"},
        aliases=["Douglas Noel Adams"],
    )


class TestConnect:
    """Connecting and configuring the index."""

    def test_connects_and_configures_the_index(self) -> None:
        """The index is created and configured on connect."""
        with patch("models.services.meilisearch.client.meilisearch") as meili:
            client = MeilisearchClient(host="meilisearch", port=7700)

            assert client.connect() is True
            assert client.url == "http://meilisearch:7700"

        meili.Client.assert_called_once_with("http://meilisearch:7700", None)
        meili.Client.return_value.create_index.assert_called_once_with(
            "entitybase", {"primaryKey": PRIMARY_KEY}
        )
        client.index.update_searchable_attributes.assert_called_once_with(
            SEARCHABLE_ATTRIBUTES
        )
        client.index.update_filterable_attributes.assert_called_once_with(
            FILTERABLE_ATTRIBUTES
        )

    def test_survives_an_index_that_already_exists(self) -> None:
        """Re-running the bootstrap on an existing index is not an error."""
        with patch("models.services.meilisearch.client.meilisearch") as meili:
            meili.Client.return_value.create_index.side_effect = RuntimeError(
                "index_already_exists"
            )
            client = MeilisearchClient()

            assert client.connect() is True

    def test_passes_the_api_key_when_set(self) -> None:
        """A protected Meilisearch is given its key."""
        with patch("models.services.meilisearch.client.meilisearch") as meili:
            MeilisearchClient(api_key="secret").connect()

        meili.Client.assert_called_once_with("http://localhost:7700", "secret")

    def test_reports_an_unusable_library(self) -> None:
        """A library that cannot be reached leaves the client disconnected."""
        with patch("models.services.meilisearch.client.meilisearch", None):
            client = MeilisearchClient()

            assert client.connect() is False
            assert client.index is None

    def test_reports_a_failing_connection(self) -> None:
        """A server that is not there does not raise."""
        with patch(
            "models.services.meilisearch.client.meilisearch.Client",
            side_effect=RuntimeError("connection refused"),
        ):
            client = MeilisearchClient()

            assert client.connect() is False
            assert client.index is None

    def test_reports_failing_index_settings(self) -> None:
        """An index whose settings cannot be set still counts as connected."""
        with patch("models.services.meilisearch.client.meilisearch") as meili:
            client = MeilisearchClient()
            meili.Client.return_value.index.return_value.update_searchable_attributes.side_effect = (
                RuntimeError("read-only index")
            )

            assert client.connect() is True


class TestIndexDocument:
    """Writing documents."""

    def test_indexes_a_document(self, client: MeilisearchClient) -> None:
        """The document is added to the index under the id primary key."""
        client.index.add_documents.return_value = MagicMock(task_uid=1)

        assert client.index_document("Q42", document()) is True

        client.index.add_documents.assert_called_once_with(
            [document().model_dump(mode="json")], primary_key=PRIMARY_KEY
        )

    def test_reports_rejected_documents(self, client: MeilisearchClient) -> None:
        """A rejected document is reported."""
        client.index.add_documents.side_effect = RuntimeError("bad document")

        assert client.index_document("Q42", document()) is False

    def test_reports_a_failed_task(self, client: MeilisearchClient) -> None:
        """A task Meilisearch itself fails is reported, not assumed good."""
        client.index.add_documents.return_value = MagicMock(task_uid=1)
        client.client.get_task.return_value = MagicMock(
            status="failed", error="index_primary_key_multiple_candidates_found"
        )

        assert client.index_document("Q42", document()) is False

    def test_reports_a_task_that_never_finishes(
        self, client: MeilisearchClient
    ) -> None:
        """A task that times out is reported, not assumed good."""
        client.index.add_documents.return_value = MagicMock(task_uid=1)
        client.client.wait_for_task.side_effect = TimeoutError("timed out")

        assert client.index_document("Q42", document()) is False

    def test_assumes_success_without_a_task(self, client: MeilisearchClient) -> None:
        """A client that reports no task at all has nothing to wait for."""
        client.index.add_documents.return_value = None

        assert client.index_document("Q42", document()) is True

    def test_reports_a_disconnected_client(self) -> None:
        """Indexing without a connection fails instead of raising."""
        assert MeilisearchClient().index_document("Q42", document()) is False


class TestDeleteDocument:
    """Removing documents."""

    def test_deletes_a_document(self, client: MeilisearchClient) -> None:
        """The document is removed by ID."""
        client.index.delete_document.return_value = MagicMock(task_uid=2)

        assert client.delete_document("Q42") is True

        client.index.delete_document.assert_called_once_with("Q42")

    def test_reports_rejected_deletions(self, client: MeilisearchClient) -> None:
        """A rejected deletion is reported."""
        client.index.delete_document.side_effect = RuntimeError("nope")

        assert client.delete_document("Q42") is False


class TestGetDocument:
    """Reading one document."""

    def test_returns_the_indexed_document(self, client: MeilisearchClient) -> None:
        """A stored document comes back as a model."""
        client.index.get_document.return_value = document().model_dump(mode="json")

        response = client.get_document("Q42")

        assert response.data is not None
        assert response.data.id == "Q42"
        assert response.index == "entitybase"

    def test_returns_nothing_for_an_unindexed_entity(
        self, client: MeilisearchClient
    ) -> None:
        """An entity that was never indexed has no document."""
        client.index.get_document.side_effect = RuntimeError("not found")

        response = client.get_document("Q42")

        assert response.data is None

    def test_returns_nothing_when_disconnected(self) -> None:
        """Reading without a connection yields no document."""
        assert MeilisearchClient().get_document("Q42").data is None


class TestSearch:
    """Querying the index."""

    def test_returns_hits_and_the_total(self, client: MeilisearchClient) -> None:
        """Hits, the estimated total and the query time are returned."""
        client.index.search.return_value = {
            "hits": [
                {
                    "id": "Q42",
                    "type": "item",
                    "label": "Douglas Adams",
                    "description": "English writer",
                    "lastrevid": 7,
                }
            ],
            "estimatedTotalHits": 1,
            "processingTimeMs": 3,
        }

        hits, total, took = client.search("douglas")

        assert total == 1
        assert took == 3
        assert len(hits) == 1
        assert hits[0].entity_id == "Q42"
        assert hits[0].entity_type == "item"
        assert hits[0].label == "Douglas Adams"

    def test_filters_by_entity_type(self, client: MeilisearchClient) -> None:
        """A type filter is passed to Meilisearch, not applied locally."""
        client.index.search.return_value = {"hits": []}

        client.search("douglas", entity_type="lexeme")

        client.index.search.assert_called_once_with(
            "douglas", {"limit": 20, "offset": 0, "filter": 'type = "lexeme"'}
        )

    def test_searches_all_types_without_a_filter(
        self, client: MeilisearchClient
    ) -> None:
        """No type filter is sent when the query spans every type."""
        client.index.search.return_value = {"hits": []}

        client.search("douglas", limit=5, offset=10)

        client.index.search.assert_called_once_with(
            "douglas", {"limit": 5, "offset": 10}
        )

    def test_returns_no_hits_for_a_failing_query(
        self, client: MeilisearchClient
    ) -> None:
        """A failed query is reported as no results."""
        client.index.search.side_effect = RuntimeError("index missing")

        assert client.search("douglas") == ([], 0, 0)

    def test_returns_no_hits_when_disconnected(self) -> None:
        """Searching without a connection yields nothing."""
        assert MeilisearchClient().search("douglas") == ([], 0, 0)

    def test_copes_with_hits_missing_fields(self, client: MeilisearchClient) -> None:
        """An index written by an older version still returns usable hits."""
        client.index.search.return_value = {"hits": [{"id": "Q1"}]}

        hits, total, _ = client.search("douglas")

        assert hits[0].entity_id == "Q1"
        assert hits[0].label == ""
        assert total == 1


class TestClose:
    """Closing the connection."""

    def test_close_drops_the_connection(self, client: MeilisearchClient) -> None:
        """A closed client is disconnected."""
        client.close()

        assert client.client is None
        assert client.index is None