"""User-related routes."""

from fastapi import APIRouter, HTTPException, Request, Depends, Query

from models.rest_api.entitybase.v1.handlers.user import UserHandler
from models.rest_api.entitybase.v1.handlers.user_activity import UserActivityHandler
from models.data.rest_api.v1.entitybase.request import (
    UserCreateRequest,
    WatchlistToggleRequest,
)
from models.data.rest_api.v1.entitybase.response import (
    WatchlistToggleResponse,
    UserCreateResponse,
)
from models.data.rest_api.v1.entitybase.response import UserStatsResponse
from models.data.rest_api.v1.entitybase.response import UserResponse
from models.data.rest_api.v1.entitybase.response import UserActivityResponse
from models.rest_api.utils import raise_validation_error, validate_state_clients
from models.rest_api.dependencies import require_self
from pydantic import BaseModel

from models.data.rest_api.v1.entitybase.response.user_settings import (
    SettingsStoredResponse,
    UserSettingsResponse,
)
from models.data.rest_api.v1.entitybase.response.user_list import (
    UserListItem,
    UserListResponse,
)

users_router = APIRouter(tags=["users"])


class UserActivityQuery(BaseModel):
    """Query parameters for user activity."""

    activity_type: str | None = Query(
        None, alias="type", description="Activity type filter"
    )
    hours: int = Query(24, ge=1, description="Hours to look back")
    limit: int = Query(50, ge=1, description="Max activities to return")
    offset: int = Query(0, ge=0, description="Offset for pagination")


def get_user_activity_query(
    activity_type: str | None = Query(None, alias="type"),
    hours: int = Query(24, ge=1),
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
) -> UserActivityQuery:
    """Dependency to extract query parameters."""
    return UserActivityQuery(
        activity_type=activity_type,
        hours=hours,
        limit=limit,
        offset=offset,
    )


@users_router.post("/users", response_model=UserCreateResponse)
async def create_user(request: UserCreateRequest, req: Request) -> UserCreateResponse:
    """Create a new user."""
    state = req.app.state.state_handler
    validate_state_clients(state)

    handler = UserHandler(state=state)
    try:
        result = await handler.create_user(request)
        if not isinstance(result, UserCreateResponse):
            raise_validation_error("Invalid response type", status_code=500)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@users_router.get("/users", response_model=UserListResponse)
def list_users(
    req: Request,
    limit: int = Query(10, ge=1, le=100, description="Maximum users to return"),
    offset: int = Query(0, ge=0, description="Number of users to skip"),
) -> UserListResponse:
    """List users with usernames and activity, paginated."""
    state = req.app.state.state_handler
    validate_state_clients(state)
    rows = state.db_client.user_repository.list_users(
        limit=limit, offset=offset
    )
    return UserListResponse(
        users=[UserListItem.model_validate(row) for row in rows],
        count=len(rows),
    )


@users_router.get("/users/stat", response_model=UserStatsResponse)
def get_user_stats(req: Request) -> UserStatsResponse:
    """Get user statistics."""
    state = req.app.state.state_handler
    handler = UserHandler(state=state)
    try:
        stats = handler.get_user_stats()
        return stats
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@users_router.get("/users/{user_id}/settings")
def get_user_settings(
    user_id: int, req: Request, _: int = Depends(require_self)
) -> UserSettingsResponse:
    """Get the UI settings stored for a user. Only the owner may read them."""
    state = req.app.state.state_handler
    if not state.db_client.user_repository.user_exists(user_id):  # type: ignore[union-attr]
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    preferences: dict = state.db_client.user_repository.get_ui_preferences(user_id) or {}
    return UserSettingsResponse.model_validate(preferences)


@users_router.put("/users/{user_id}/settings")
def set_user_settings(
    user_id: int,
    request: dict,
    req: Request,
    _: int = Depends(require_self),
) -> SettingsStoredResponse:
    """Store UI settings for a user (arbitrary JSON, e.g. language chain).

    Only the owner may write them: the path id is otherwise just a number the
    client picks, and preferences are per-user state.
    """
    if not isinstance(request, dict):
        raise HTTPException(status_code=400, detail="Settings must be a JSON object")
    state = req.app.state.state_handler
    if not state.db_client.user_repository.user_exists(user_id):  # type: ignore[union-attr]
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    ok = state.db_client.user_repository.set_ui_preferences(user_id, request)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to store settings")
    return SettingsStoredResponse(stored=True)


@users_router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, req: Request) -> UserResponse:
    """Get user information by MediaWiki user ID."""
    state = req.app.state.state_handler
    validate_state_clients(state)
    handler = UserHandler(state=state)
    try:
        result = handler.get_user(user_id)
        if not isinstance(result, UserResponse):
            raise_validation_error("Invalid response type", status_code=500)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@users_router.delete("/users/{user_id}")
async def delete_user(
    user_id: int, req: Request, _: int = Depends(require_self)
) -> None:
    """Delete a user by ID. Only the account's own token may delete it."""
    state = req.app.state.state_handler
    validate_state_clients(state)
    handler = UserHandler(state=state)
    try:
        await handler.delete_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@users_router.put(
    "/users/{user_id}/watchlist/toggle", response_model=WatchlistToggleResponse
)
async def toggle_watchlist(
    user_id: int,
    request: WatchlistToggleRequest,
    req: Request,
    _: int = Depends(require_self),
) -> WatchlistToggleResponse:
    """Enable or disable watchlist for the authenticated user."""
    state = req.app.state.state_handler
    validate_state_clients(state)
    handler = UserHandler(state=state)
    try:
        result = await handler.toggle_watchlist(user_id, request)
        if not isinstance(result, WatchlistToggleResponse):
            raise_validation_error("Invalid response type", status_code=500)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@users_router.get("/users/{user_id}/activity", response_model=UserActivityResponse)
def get_user_activity(
    user_id: int,
    req: Request,
    query: UserActivityQuery = Depends(get_user_activity_query),
    _: int = Depends(require_self),
) -> UserActivityResponse:
    """Get the authenticated user's activity with filtering."""
    state = req.app.state.state_handler
    handler = UserActivityHandler(state=state)
    try:
        return handler.get_user_activity(
            user_id, query.activity_type, query.hours, query.limit, query.offset
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
