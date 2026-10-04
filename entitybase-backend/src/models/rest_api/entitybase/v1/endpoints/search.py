"""Entity search routes."""

import logging
from typing import Annotated

from fastapi import APIRouter, Path, Query, Request

from models.data.infrastructure.meilisearch import MeilisearchDocumentResponse
from models.data.rest_api.v1.entitybase.response import SearchResponse
from models.rest_api.entitybase.v1.handlers.search import MAX_LIMIT, SearchHandler

logger = logging.getLogger(__name__)

ENTITY_ID_PATH_PATTERN = r"^[QPL]\d+$"

SingleEntityId = Annotated[str, Path(pattern=ENTITY_ID_PATH_PATTERN)]

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search_entities(
    req: Request,
    q: Annotated[str, Query(description="What to search for", min_length=1)],
    type: Annotated[
        str,
        Query(description="Only search this entity type; omit to search all"),
    ] = "",
    limit: Annotated[
        int, Query(description="Maximum number of hits", ge=1, le=MAX_LIMIT)
    ] = 20,
    offset: Annotated[int, Query(description="Number of hits to skip")] = 0,
) -> SearchResponse:
    """Search entities by label, description and alias."""
    logger.debug(f"search_entities called with q={q!r}, type={type!r}")
    state = req.app.state.state_handler
    return SearchHandler(state=state).search(
        query=q, entity_type=type, limit=limit, offset=offset
    )


@router.get(
    "/entities/{entity_id}/meilisearch",
    response_model=MeilisearchDocumentResponse,
)
async def get_meilisearch_document(
    entity_id: SingleEntityId,
    req: Request,
) -> MeilisearchDocumentResponse:
    """Get the document that search holds for an entity.

    Useful to see what the indexer produced without rebuilding it.
    """
    logger.debug(f"get_meilisearch_document called with entity_id={entity_id}")
    state = req.app.state.state_handler
    return SearchHandler(state=state).get_indexed_document(entity_id)


@router.get(
    "/entities/{entity_id}/meilisearch/preview",
    response_model=MeilisearchDocumentResponse,
)
async def preview_meilisearch_document(
    entity_id: SingleEntityId,
    req: Request,
) -> MeilisearchDocumentResponse:
    """Build the search document an entity would be indexed with right now."""
    logger.debug(f"preview_meilisearch_document called with entity_id={entity_id}")
    state = req.app.state.state_handler
    return SearchHandler(state=state).build_document_preview(entity_id)