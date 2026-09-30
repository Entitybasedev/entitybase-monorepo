"""Contract tests for the per-user UI settings endpoints."""

import sys

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, "src")

HEADERS = {"X-User-ID": "90001", "X-Edit-Summary": "test"}


@pytest.mark.contract
@pytest.mark.asyncio
async def test_settings_roundtrip(api_prefix: str) -> None:
    """Register a user, store settings and read them back."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create = await client.post(
            f"{api_prefix}/users", json={"user_id": 90001}, headers=HEADERS
        )
        assert create.status_code == 200

        empty = await client.get(f"{api_prefix}/users/90001/settings")
        assert empty.status_code == 200
        assert empty.json() == {}

        stored = await client.put(
            f"{api_prefix}/users/90001/settings",
            json={"ui": {"fallbackChain": ["da", "sv", "en"]}},
        )
        assert stored.status_code == 200
        assert stored.json() == {"stored": True}

        fetched = await client.get(f"{api_prefix}/users/90001/settings")
        assert fetched.status_code == 200
        assert fetched.json() == {"ui": {"fallbackChain": ["da", "sv", "en"]}}


@pytest.mark.contract
@pytest.mark.asyncio
async def test_settings_unknown_user_returns_404(api_prefix: str) -> None:
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        get = await client.get(f"{api_prefix}/users/999999999/settings")
        assert get.status_code == 404

        put = await client.put(
            f"{api_prefix}/users/999999999/settings", json={"ui": {}}
        )
        assert put.status_code == 404


@pytest.mark.contract
@pytest.mark.asyncio
async def test_settings_must_be_an_object(api_prefix: str) -> None:
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        put = await client.put(
            f"{api_prefix}/users/90001/settings", json=["not", "an", "object"]
        )
        assert put.status_code in {400, 422}
