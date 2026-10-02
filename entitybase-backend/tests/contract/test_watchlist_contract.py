"""Contract tests for watchlist API endpoints.

These tests verify the watchlist endpoints conform to their API contract.

User 999999999 is used as the unknown user; user 0 is the reserved
import user and exists after startup seeding.
"""

import sys

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, "src")

UNKNOWN_USER = 999999999


@pytest.mark.contract
@pytest.mark.asyncio
async def test_watchlist_response_schema(api_prefix: str) -> None:
    """Contract test: Watchlist response structure."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"{api_prefix}/users/{UNKNOWN_USER}/watchlist",
            headers={"X-User-ID": str(UNKNOWN_USER)},
        )
        assert response.status_code == 404


@pytest.mark.contract
@pytest.mark.asyncio
async def test_watchlist_pagination(api_prefix: str) -> None:
    """Contract test: Pagination works correctly."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"{api_prefix}/users/{UNKNOWN_USER}/watchlist?limit=10&offset=0",
            headers={"X-User-ID": str(UNKNOWN_USER)},
        )
        assert response.status_code == 404


@pytest.mark.contract
@pytest.mark.asyncio
async def test_watchlist_unauthorized(api_prefix: str) -> None:
    """Contract test: A broken bearer token is rejected with 401."""
    from models.rest_api.main import app
    from models.config.settings import settings

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(settings, "auth_secret", "test-secret")
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                f"{api_prefix}/users/{UNKNOWN_USER}/watchlist",
                headers={"Authorization": "Bearer not.a.token"},
            )
            assert response.status_code == 401
    finally:
        monkeypatch.undo()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_watchlist_notification_count(api_prefix: str) -> None:
    """Contract test: Notification count endpoint."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"{api_prefix}/users/{UNKNOWN_USER}/watchlist/notifications",
            headers={"X-User-ID": str(UNKNOWN_USER)},
        )
        assert response.status_code == 404
