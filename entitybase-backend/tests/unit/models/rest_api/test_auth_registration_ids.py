"""Tests for the user id assigned at registration.

Ids come from MAX(user_id) + 1, so deleting the highest account makes its id
available again - including the credentials row it left behind, which is what
made registration fail with a duplicate key.
"""

import sys
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, "src")

from models.data.common import OperationResult  # noqa: E402
from models.rest_api.entitybase.v1.routes.auth import auth_router  # noqa: E402


def build_client(
    existing_users: set[int], orphaned_credentials: set[int]
) -> tuple[AsyncClient, MagicMock]:
    """An app whose user repository models the two tables separately.

    get_next_user_id behaves like the real one: one more than the highest id
    held by either table, so a skipped candidate moves the allocator forward
    instead of being offered again. Returns the client and the repository mock.
    """
    app = FastAPI()
    state = MagicMock()
    repo = state.db_client.user_repository
    taken = existing_users | orphaned_credentials
    repo.get_credentials_by_username.return_value = None
    repo.user_exists.side_effect = lambda user_id: user_id in existing_users
    repo.credentials_exist.side_effect = lambda user_id: user_id in orphaned_credentials
    repo.create_user.side_effect = lambda user_id: OperationResult(
        success=user_id not in existing_users
    )
    repo.create_credentials.return_value = OperationResult(success=True)
    repo.get_next_user_id.side_effect = lambda: (max(taken) + 1) if taken else 90001
    app.state.state_handler = state
    app.include_router(auth_router, prefix="/v1")
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    return client, repo


async def _register(client: AsyncClient, username: str):
    return await client.post(
        "/v1/auth/register", json={"username": username, "password": "secret"}
    )


@pytest.mark.asyncio
async def test_registration_works_without_orphans() -> None:
    client, _ = build_client(existing_users=set(), orphaned_credentials=set())
    async with client:
        response = await _register(client, "fresh")

    assert response.status_code == 200
    assert response.json()["user_id"] == 90001


@pytest.mark.asyncio
async def test_registration_skips_an_id_with_orphaned_credentials() -> None:
    """A leftover credential row must not fail registration with a 500.

    The allocator is pinned to keep offering the same id, so the guard in the
    route is the only thing standing between the orphan and a duplicate key.
    """
    client, repo = build_client(existing_users=set(), orphaned_credentials={90001})
    repo.get_next_user_id.side_effect = None
    repo.get_next_user_id.return_value = 90001

    async with client:
        response = await _register(client, "after-deletion")

    assert response.status_code == 503  # offered 5 times, always the same id
    # It never tried to insert credentials for the orphaned id
    assert repo.create_user.called is False


@pytest.mark.asyncio
async def test_registration_advances_past_an_orphaned_id() -> None:
    """With an allocator that steps over orphans, registration just works."""
    client, _ = build_client(existing_users=set(), orphaned_credentials={90001})
    async with client:
        response = await _register(client, "after-deletion-2")

    assert response.status_code == 200
    assert response.json()["user_id"] != 90001


@pytest.mark.asyncio
async def test_registration_gives_up_after_repeated_collisions() -> None:
    """Persistent insert failures end in 503, not an endless loop.

    The allocator keeps offering an id that looks free but cannot be created,
    as happens when a concurrent registration wins the insert first.
    """
    client, repo = build_client(existing_users=set(), orphaned_credentials=set())
    repo.get_next_user_id.side_effect = None
    repo.get_next_user_id.return_value = 90001
    # side_effect wins over return_value, so clear it first
    repo.create_user.side_effect = None
    repo.create_user.return_value = OperationResult(
        success=False, error="Duplicate entry"
    )
    async with client:
        response = await _register(client, "losing-the-race")

    assert response.status_code == 503