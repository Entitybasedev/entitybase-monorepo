"""Entity search handler.

Search is served from the Meilisearch index the indexer worker maintains; the
database is not touched. When Meilisearch is not configured or not reachable
the handler says so instead of failing the request silently.
"""

import logging

from models.data.infrastructure.meilisearch import MeilisearchDocumentResponse
from models.data.infrastructure.s3.enums import MetadataType
from models.data.rest_api.v1.entitybase.response import (
    SearchHit,
    SearchResponse,
)
from models.rest_api.entitybase.v1.handler import Handler
from models.rest_api.entitybase.v1.handlers.entity.read import EntityReadHandler
from models.rest_api.utils import raise_validation_error
from models.services.meilisearch import (
    MeilisearchClient,
    RevisionRef,
    build_document,
    entity_type_from_id,
)

logger = logging.getLogger(__name__)

SEARCHABLE_TYPES = ["", "item", "property", "lexeme"]
MAX_LIMIT = 100


class SearchHandler(Handler):
    """Queries the Meilisearch index."""

    def search(
        self,
        query: str,
        entity_type: str = "",
        limit: int = 20,
        offset: int = 0,
    ) -> SearchResponse:
        """Search entities by label, description and alias.

        Args:
            query: what to search for.
            entity_type: only return this entity type; empty means all types.
            limit: maximum number of hits (1-100).
            offset: number of hits to skip.

        Returns:
            The matching entities.
        """
        self._validate(query, entity_type, limit, offset)
        client = self._connected_client()

        hits, total, took = client.search(
            query, limit=limit, offset=offset, entity_type=entity_type
        )
        logger.info(
            f"Search '{query}' (type={entity_type or 'all'}) returned {len(hits)} of {total} hits in {took}ms"
        )

        return SearchResponse(
            query=query,
            type=entity_type,
            index=client.index_name,
            hits=[
                SearchHit(
                    entity_id=hit.entity_id,
                    type=hit.entity_type,
                    label=hit.label,
                    description=hit.description,
                    lastrevid=hit.lastrevid,
                )
                for hit in hits
            ],
            estimated_total_hits=total,
            limit=limit,
            offset=offset,
            processing_time_ms=took,
        )

    def get_indexed_document(self, entity_id: str) -> MeilisearchDocumentResponse:
        """Get the document the index holds for one entity.

        Args:
            entity_id: the entity ID, e.g. Q42.

        Returns:
            The indexed document.
        """
        client = self._connected_client()
        response = client.get_document(entity_id)
        if response.data is None:
            raise_validation_error(
                f"No indexed document for entity {entity_id}", status_code=404
            )
        return response

    def build_document_preview(self, entity_id: str) -> MeilisearchDocumentResponse:
        """Build the document that would be indexed for an entity right now.

        Useful to see how an entity looks to search without waiting for the
        indexer to pick it up. It reads the database only, so it also works
        while Meilisearch is down.

        Args:
            entity_id: the entity ID, e.g. Q42.

        Returns:
            The document built from the current revision.
        """
        entity = EntityReadHandler(state=self.state).get_entity(entity_id)
        document = build_document(
            RevisionRef(
                entity_id=entity_id,
                entity_type=entity_type_from_id(entity_id),
                lastrevid=entity.rev_id,
                modified=entity.entity_data.created_at,
            ),
            entity.entity_data.revision,
            self._load_term,
        )
        logger.debug(f"Built the search document for {entity_id} on request")
        return MeilisearchDocumentResponse(
            data=document, index=self.state.settings.meilisearch_index
        )

    def _validate(
        self, query: str, entity_type: str, limit: int, offset: int
    ) -> None:
        """Reject a search the API cannot answer sensibly."""
        if not query.strip():
            raise_validation_error("Search query must not be empty", status_code=400)
        if entity_type not in SEARCHABLE_TYPES:
            raise_validation_error(
                f"Unknown entity type: {entity_type}", status_code=400
            )
        if limit < 1 or limit > MAX_LIMIT:
            raise_validation_error(
                f"Limit must be between 1 and {MAX_LIMIT}", status_code=400
            )
        if offset < 0:
            raise_validation_error("Offset must not be negative", status_code=400)
        logger.debug(
            f"Searching '{query.strip()}' for {entity_type or 'all types'}, limit={limit}, offset={offset}"
        )

    def _connected_client(self) -> MeilisearchClient:
        """Get the Meilisearch client, or report search as unavailable."""
        client = self.state.meilisearch_client
        if client.index is None:
            raise_validation_error(
                "Search is not available: Meilisearch is not reachable",
                status_code=503,
            )
        return client

    def _load_term(self, metadata_type: MetadataType, content_hash: int) -> str | None:
        """Load the text of one content-addressed term."""
        metadata = self.state.s3_client.load_metadata(metadata_type, content_hash)
        if metadata is None:
            return None
        return str(metadata.data)