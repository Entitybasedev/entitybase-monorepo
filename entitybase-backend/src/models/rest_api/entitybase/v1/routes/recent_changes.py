"""Recent changes routes."""

import logging

from fastapi import APIRouter, Query, Request

from models.data.rest_api.v1.entitybase.request import EntityChangeType
from models.data.rest_api.v1.entitybase.response.recent_changes import (
    RecentChangeEntry,
)
from models.rest_api.utils import raise_validation_error, validate_state_clients

logger = logging.getLogger(__name__)

recent_changes_router = APIRouter(tags=["recent changes"])


@recent_changes_router.get(
    "/recentchanges",
    response_model=list[RecentChangeEntry],
)
def get_recent_changes(
    req: Request,
    limit: int = Query(50, ge=1, le=100, description="Maximum entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    change_type: str | None = Query(
        None,
        description="Filter by granular change type (e.g. statement_add)",
    ),
) -> list[RecentChangeEntry]:
    """Get the most recent changes across all entities."""
    state = req.app.state.state_handler
    validate_state_clients(state)

    change_filter: EntityChangeType | None = None
    if change_type:
        try:
            change_filter = EntityChangeType(change_type)
        except ValueError:
            valid = ", ".join(t.value for t in EntityChangeType)
            raise_validation_error(
                f"Invalid change_type. Must be one of: {valid}", status_code=400
            )

    rows = state.db_client.user_repository.get_recent_changes(
        limit=limit, offset=offset, change_type=change_filter
    )
    logger.debug(f"Returning {len(rows)} recent changes")
    return [RecentChangeEntry.model_validate(row) for row in rows]
