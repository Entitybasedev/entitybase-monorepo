"""Unit tests for the search handler."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from models.rest_api.entitybase.v1.handlers.search import SearchHandler


@pytest.fixture
def mock_state():
    """A state whose Meilisearch client is mocked and connected."""
    state = MagicMock()
    client = MagicMock()
    client.index = MagicMock()
    client.index_name = "entitybase"
    client.search.return_value = (
        [
            MagicMock(
                entity_id="Q42",
                entity_type="item",
                label="Douglas Adams",
                description="English writer",
                lastrevid=7,
            )
        ],
        1,
        3,
    )
    state.meilisearch_client = client
    return state


@pytest.fixture
def handler(mock_state) -> SearchHandler:
    """A search handler over the mocked state."""
    return SearchHandler(state=mock_state)


class TestSearch:
    """Querying the index."""

    def test_returns_hits(self, handler: SearchHandler) -> None:
        """Hits come back with the query echoed back."""
        result = handler.search("douglas")

        assert result.query == "douglas"
        assert result.index == "entitybase"
        assert result.estimated_total_hits == 1
        assert result.processing_time_ms == 3
        assert len(result.hits) == 1
        assert result.hits[0].entity_id == "Q42"
        assert result.hits[0].type == "item"
        assert result.hits[0].label == "Douglas Adams"

    def test_searches_every_type_by_default(self, handler: SearchHandler) -> None:
        """No type filter is sent when the query spans every type."""
        handler.search("douglas")

        handler.state.meilisearch_client.search.assert_called_once_with(
            "douglas", limit=20, offset=0, entity_type=""
        )

    def test_filters_by_type(self, handler: SearchHandler) -> None:
        """A type filter is passed on to Meilisearch."""
        result = handler.search("douglas", entity_type="lexeme")

        handler.state.meilisearch_client.search.assert_called_once_with(
            "douglas", limit=20, offset=0, entity_type="lexeme"
        )
        assert result.type == "lexeme"

    def test_passes_paging_through(self, handler: SearchHandler) -> None:
        """Limit and offset reach Meilisearch."""
        handler.search("douglas", limit=5, offset=10)

        handler.state.meilisearch_client.search.assert_called_once_with(
            "douglas", limit=5, offset=10, entity_type=""
        )

    def test_rejects_an_empty_query(self, handler: SearchHandler) -> None:
        """A blank query is a client error, not an empty result."""
        with pytest.raises(HTTPException) as exc:
            handler.search("   ")

        assert exc.value.status_code == 400

    def test_rejects_an_unknown_type(self, handler: SearchHandler) -> None:
        """Only the three entity types can be filtered on."""
        with pytest.raises(HTTPException) as exc:
            handler.search("douglas", entity_type="user")

        assert exc.value.status_code == 400

    @pytest.mark.parametrize("limit", [0, -1, 101])
    def test_rejects_a_limit_outside_the_range(
        self, handler: SearchHandler, limit: int
    ) -> None:
        """The limit is bounded, so a page cannot ask for everything."""
        with pytest.raises(HTTPException) as exc:
            handler.search("douglas", limit=limit)

        assert exc.value.status_code == 400

    def test_rejects_a_negative_offset(self, handler: SearchHandler) -> None:
        """Paging cannot start before the beginning."""
        with pytest.raises(HTTPException) as exc:
            handler.search("douglas", offset=-1)

        assert exc.value.status_code == 400

    def test_reports_search_as_unavailable(
        self, handler: SearchHandler, mock_state
    ) -> None:
        """A Meilisearch that cannot be reached is a 503, not a 500."""
        mock_state.meilisearch_client.index = None

        with pytest.raises(HTTPException) as exc:
            handler.search("douglas")

        assert exc.value.status_code == 503
        assert "Meilisearch" in str(exc.value.detail)


class TestGetIndexedDocument:
    """Reading the document of one entity."""

    def test_returns_the_indexed_document(
        self, handler: SearchHandler, mock_state
    ) -> None:
        """The stored document is returned as stored."""
        document = MagicMock()
        document.model_dump.return_value = {"id": "Q42", "label": "Douglas Adams"}
        mock_state.meilisearch_client.get_document.return_value = MagicMock(
            data=document, index="entitybase"
        )

        response = handler.get_indexed_document("Q42")

        assert response.data is document
        assert response.index == "entitybase"

    def test_reports_an_unindexed_entity(
        self, handler: SearchHandler, mock_state
    ) -> None:
        """An entity that was never indexed is a 404."""
        mock_state.meilisearch_client.get_document.return_value = MagicMock(data=None)

        with pytest.raises(HTTPException) as exc:
            handler.get_indexed_document("Q42")

        assert exc.value.status_code == 404

    def test_reports_search_as_unavailable(
        self, handler: SearchHandler, mock_state
    ) -> None:
        """Without Meilisearch there is no document to show."""
        mock_state.meilisearch_client.index = None

        with pytest.raises(HTTPException) as exc:
            handler.get_indexed_document("Q42")

        assert exc.value.status_code == 503


class TestBuildDocumentPreview:
    """Building the document an entity would be indexed with."""

    def test_builds_the_document_from_the_current_revision(
        self, handler: SearchHandler, mock_state
    ) -> None:
        """The preview resolves the terms of the entity's head revision."""
        mock_state.settings.meilisearch_index = "entitybase"
        mock_state.s3_client.load_metadata.side_effect = (
            lambda metadata_type, content_hash: MagicMock(data="Douglas Adams")
        )

        with patch(
            "models.rest_api.entitybase.v1.handlers.search.EntityReadHandler"
        ) as read_handler:
            read_handler.return_value.get_entity.return_value = MagicMock(
                rev_id=7,
                entity_data=MagicMock(
                    revision={"hashes": {"labels": {"en": 11}}},
                    created_at="2026-01-01T00:00:00Z",
                ),
            )

            response = handler.build_document_preview("Q42")

        assert response.index == "entitybase"
        assert response.data is not None
        assert response.data.id == "Q42"
        assert response.data.type == "item"
        assert response.data.label == "Douglas Adams"
        assert response.data.lastrevid == 7

    def test_reports_search_as_unavailable(
        self, handler: SearchHandler, mock_state
    ) -> None:
        """The preview needs no Meilisearch, so it works without one."""
        mock_state.meilisearch_client.index = None
        mock_state.settings.meilisearch_index = "entitybase"
        mock_state.s3_client.load_metadata.side_effect = (
            lambda metadata_type, content_hash: MagicMock(data="Douglas Adams")
        )

        with patch(
            "models.rest_api.entitybase.v1.handlers.search.EntityReadHandler"
        ) as read_handler:
            read_handler.return_value.get_entity.return_value = MagicMock(
                rev_id=7,
                entity_data=MagicMock(
                    revision={"hashes": {}}, created_at="2026-01-01T00:00:00Z"
                ),
            )

            response = handler.build_document_preview("Q42")

        assert response.data is not None
        assert response.data.id == "Q42"