"""Route-level tests for account ownership on the users router.

These run the real AuthMiddleware and the real router through ASGI, with only
the data layer stubbed, so they check the wiring: that the middleware
publishes the token's user and that require_self actually guards the route.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from models.config.settings import settings
from models.data.rest_api.v1.entitybase.response import UserResponse
from models.rest_api.entitybase.v1.routes.users import users_router
from models.rest_api.entitybase.v1.services.auth_service import create_token

EXISTING_USER_IDS = {42, 90099}


def auth_middleware() -> type:
    """The app's real auth middleware."""
    from models.rest_api.main import AuthMiddleware

    return AuthMiddleware


def build_client() -> AsyncClient:
    """An app with the real middleware and router, and a stubbed database."""
    from models.data.common import OperationResult

    app = FastAPI()
    state = MagicMock()
    state.db_client.user_repository.user_exists.side_effect = lambda user_id: (
        user_id in EXISTING_USER_IDS
    )
    state.db_client.user_repository.get_ui_preferences.return_value = {
        "ui": {"language": "sv"}
    }
    state.db_client.user_repository.set_ui_preferences.return_value = True
    state.db_client.user_repository.delete_user.return_value = OperationResult(
        success=True
    )
    state.db_client.user_repository.get_user.return_value = UserResponse(
        user_id=42,
        created_at="2026-01-01T00:00:00",
        preferences=None,
    )
    state.user_change_stream_producer = AsyncMock()
    app.state.state_handler = state
    app.include_router(users_router, prefix="/v1")

    app.add_middleware(auth_middleware())
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def token_for(user_id: int) -> str:
    """A bearer token for the given user id."""
    return create_token(
        user_id=user_id,
        username=f"user{user_id}",
        secret=settings.auth_signing_secret,
        expiry_hours=1,
    )


@pytest.mark.asyncio
async def test_owner_may_read_their_settings() -> None:
    async with build_client() as client:
        response = await client.get(
            "/v1/users/42/settings",
            headers={"Authorization": f"Bearer {token_for(42)}"},
        )

    assert response.status_code == 200
    assert response.json()["ui"]["language"] == "sv"


@pytest.mark.asyncio
async def test_other_user_may_not_read_settings() -> None:
    async with build_client() as client:
        response = await client.get(
            "/v1/users/42/settings",
            headers={"Authorization": f"Bearer {token_for(90099)}"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_other_user_may_not_write_settings() -> None:
    async with build_client() as client:
        response = await client.put(
            "/v1/users/42/settings",
            json={"ui": {"language": "de"}},
            headers={"Authorization": f"Bearer {token_for(90099)}"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_anonymous_may_not_touch_settings() -> None:
    async with build_client() as client:
        read = await client.get("/v1/users/42/settings")
        write = await client.put("/v1/users/42/settings", json={"ui": {}})

    assert read.status_code == 401
    assert write.status_code == 401


@pytest.mark.asyncio
async def test_other_user_may_not_delete_the_account() -> None:
    async with build_client() as client:
        response = await client.delete(
            "/v1/users/42",
            headers={"Authorization": f"Bearer {token_for(90099)}"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_owner_may_delete_their_account() -> None:
    async with build_client() as client:
        response = await client.delete(
            "/v1/users/42",
            headers={"Authorization": f"Bearer {token_for(42)}"},
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_other_user_may_not_toggle_the_watchlist() -> None:
    async with build_client() as client:
        response = await client.put(
            "/v1/users/42/watchlist/toggle",
            json={"enabled": False},
            headers={"Authorization": f"Bearer {token_for(90099)}"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_other_user_may_not_read_activity() -> None:
    async with build_client() as client:
        response = await client.get(
            "/v1/users/42/activity",
            headers={"Authorization": f"Bearer {token_for(90099)}"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_owner_may_read_their_activity() -> None:
    async with build_client() as client:
        response = await client.get(
            "/v1/users/42/activity",
            headers={"Authorization": f"Bearer {token_for(42)}"},
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_public_user_lookup_still_works() -> None:
    """Reading a public profile by id is not an ownership question."""
    async with build_client() as client:
        response = await client.get("/v1/users/42")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_deleted_account_settings_return_404() -> None:
    """A token outlives its account: the owner check passes, the lookup fails."""
    app = FastAPI()
    state = MagicMock()
    state.db_client.user_repository.user_exists.return_value = False
    app.state.state_handler = state
    app.include_router(users_router, prefix="/v1")
    app.add_middleware(auth_middleware())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/v1/users/42/settings",
            headers={"Authorization": f"Bearer {token_for(42)}"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_a_client_sent_user_id_is_not_an_identity() -> None:
    """X-User-ID cannot stand in for a token."""
    async with build_client() as client:
        response = await client.get(
            "/v1/users/42/settings",
            headers={"X-User-ID": str(uuid.uuid4().int % 100000)},
        )

    assert response.status_code == 401
