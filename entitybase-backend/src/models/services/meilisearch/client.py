"""Meilisearch client.

A thin wrapper over the Meilisearch HTTP client: index bootstrap, document
writes and search. The client is optional - if the library is missing or the
server is unreachable, every operation reports failure instead of raising, so
a missing Meilisearch never takes the API down.
"""

import logging
from typing import Any

import meilisearch
from meilisearch.client import Client as MeilisearchClientType
from meilisearch.index import Index as MeilisearchIndexType
from pydantic import BaseModel, ConfigDict, Field

from models.data.infrastructure.meilisearch import (
    MeilisearchDocument,
    MeilisearchDocumentResponse,
)

logger = logging.getLogger(__name__)

# Attributes Meilisearch searches in, most relevant first
SEARCHABLE_ATTRIBUTES = ["label", "aliases", "labels", "description", "descriptions"]

# Attributes results can be filtered on
FILTERABLE_ATTRIBUTES = ["type"]

# The document field Meilisearch uses as the document id
PRIMARY_KEY = "id"

# How long to wait for Meilisearch to finish an indexing task
TASK_TIMEOUT_MS = 10_000


class MeilisearchSearchResult(BaseModel):
    """One hit of a Meilisearch query, reduced to what a search page shows."""

    model_config = ConfigDict(populate_by_name=True)

    entity_id: str = Field(default="", description="Entity ID of the hit")
    entity_type: str = Field(default="", description="item, property or lexeme")
    label: str = Field(default="", description="Primary label")
    description: str = Field(default="", description="Primary description")
    lastrevid: int = Field(default=0, description="Indexed revision")


def _as_document(response: Any) -> MeilisearchDocument | None:
    """Read a stored document into the model.

    The client returns a Document object, which is not a mapping even though
    it behaves like one.
    """
    if response is None:
        return None
    fields = response if isinstance(response, dict) else getattr(response, "__dict__", None)
    if not isinstance(fields, dict) or not fields:
        return None
    return MeilisearchDocument(**fields)


class MeilisearchClient(BaseModel):
    """Client for the entity search index."""

    model_config = {"arbitrary_types_allowed": True}

    host: str = Field(default="localhost")
    port: int = Field(default=7700)
    api_key: str = Field(default="")
    index_name: str = Field(default="entitybase")
    client: MeilisearchClientType | None = Field(default=None, exclude=True)
    index: MeilisearchIndexType | None = Field(default=None, exclude=True)

    @property
    def url(self) -> str:
        """Base URL of the Meilisearch server."""
        return f"http://{self.host}:{self.port}"

    def connect(self) -> bool:
        """Connect to Meilisearch and make sure the index is usable.

        Returns:
            True when the index is ready to search, False otherwise.
        """
        try:
            self.client = meilisearch.Client(self.url, self.api_key or None)
            self.index = self.client.index(self.index_name)
            logger.info(f"Connected to Meilisearch at {self.url}/{self.index_name}")
        except Exception as e:
            logger.error(f"Failed to connect to Meilisearch: {e}")
            self.client = None
            self.index = None
            return False

        self.ensure_index_settings()
        return True

    def ensure_index_settings(self) -> bool:
        """Create the index if needed and apply the settings search relies on.

        The primary key is set explicitly: Meilisearch cannot infer it from a
        document that has both `id` and `lastrevid`.
        """
        if self.index is None or self.client is None:
            return False
        try:
            try:
                self.client.create_index(self.index_name, {"primaryKey": PRIMARY_KEY})
            except Exception as e:
                # The index existing is the normal case, not a problem
                logger.debug(f"Index {self.index_name} not created: {e}")
            self.index.update_searchable_attributes(SEARCHABLE_ATTRIBUTES)
            self.index.update_filterable_attributes(FILTERABLE_ATTRIBUTES)
            return True
        except Exception as e:
            logger.error(f"Failed to update Meilisearch index settings: {e}")
            return False

    def index_document(self, entity_id: str, document: MeilisearchDocument) -> bool:
        """Add or replace one entity in the index.

        Returns:
            True when Meilisearch accepted the document.
        """
        if self.index is None:
            logger.error("Meilisearch client is not connected")
            return False

        try:
            task = self.index.add_documents(
                [document.model_dump(mode="json")], primary_key=PRIMARY_KEY
            )
            return self._await_task(task, f"index document {entity_id}")
        except Exception as e:
            logger.error(f"Failed to index document {entity_id}: {e}")
            return False

    def delete_document(self, entity_id: str) -> bool:
        """Remove one entity from the index.

        Returns:
            True when Meilisearch accepted the deletion.
        """
        if self.index is None:
            logger.error("Meilisearch client is not connected")
            return False

        try:
            task = self.index.delete_document(entity_id)
            return self._await_task(task, f"delete document {entity_id}")
        except Exception as e:
            logger.error(f"Failed to delete document {entity_id}: {e}")
            return False

    def get_document(self, entity_id: str) -> MeilisearchDocumentResponse:
        """Get one indexed document by entity ID.

        Returns:
            The document, or `data=None` when it is not indexed.
        """
        if self.index is None:
            logger.error("Meilisearch client is not connected")
            return MeilisearchDocumentResponse(data=None, index=self.index_name)

        try:
            response = self.index.get_document(entity_id)
        except Exception as e:
            logger.debug(f"No indexed document for {entity_id}: {e}")
            return MeilisearchDocumentResponse(data=None, index=self.index_name)

        document = _as_document(response)
        if document is None:
            return MeilisearchDocumentResponse(data=None, index=self.index_name)
        return MeilisearchDocumentResponse(data=document, index=self.index_name)

    def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        entity_type: str = "",
    ) -> tuple[list[MeilisearchSearchResult], int, int]:
        """Search the index.

        Args:
            query: the search query.
            limit: maximum number of hits to return.
            offset: number of hits to skip.
            entity_type: only return hits of this entity type; empty searches
                all types.

        Returns:
            The hits, the estimated total number of hits, and the time the
            query took in milliseconds.
        """
        if self.index is None:
            logger.error("Meilisearch client is not connected")
            return [], 0, 0

        options: dict[str, Any] = {"limit": limit, "offset": offset}
        if entity_type:
            options["filter"] = f'type = "{entity_type}"'

        try:
            response = self.index.search(query, options)
        except Exception as e:
            logger.error(f"Meilisearch query failed: {e}")
            return [], 0, 0

        hits = [
            MeilisearchSearchResult(
                entity_id=str(hit.get("id", "")),
                entity_type=str(hit.get("type", "")),
                label=str(hit.get("label", "")),
                description=str(hit.get("description", "")),
                lastrevid=int(hit.get("lastrevid", 0) or 0),
            )
            for hit in response.get("hits", [])
        ]
        total = int(response.get("estimatedTotalHits", len(hits)) or 0)
        took = int(response.get("processingTimeMs", 0) or 0)
        return hits, total, took

    def _await_task(self, task: Any, what: str) -> bool:
        """Wait for a Meilisearch task, so callers learn the real outcome.

        Indexing is asynchronous: without this an entity would count as
        indexed (and searchable) before Meilisearch accepted it.

        Returns:
            True when Meilisearch finished the task successfully.
        """
        if task is None or self.client is None:
            return True

        try:
            self.client.wait_for_task(
                task.task_uid, timeout_in_ms=TASK_TIMEOUT_MS, interval_in_ms=50
            )
            finished = self.client.get_task(task.task_uid)
        except Exception as e:
            logger.error(f"Meilisearch did not confirm {what}: {e}")
            return False

        status = getattr(finished, "status", "")
        if status != "succeeded":
            logger.error(
                f"Meilisearch failed to {what}: {getattr(finished, 'error', None)}"
            )
            return False

        logger.debug(f"Meilisearch finished {what}")
        return True

    def close(self) -> None:
        """Drop the connection."""
        self.client = None
        self.index = None