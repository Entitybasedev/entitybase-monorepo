"""Contract tests for the per-user UI settings endpoints.

Settings belong to an account, so the endpoints require the owner's bearer
token: no token is a 401 and somebody else's user id is a 403, both decided
before the account is looked up.
"""

import sys

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, "src")

PASSWORD = "wonderland"


async def _register(api_prefix: str, username: str) -> dict:
    """Register an account and return its token and user id."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"{api_prefix}/auth/register",
            json={"username": username, "password": PASSWORD},
        )
    assert response.status_code == 200
    return response.json()


def _auth(account: dict) -> dict:
    return {"Authorization": f"Bearer {account['token']}"}


@pytest.mark.contract
@pytest.mark.asyncio
async def test_settings_roundtrip(api_prefix: str) -> None:
    """Store settings as the owner and read them back."""
    from models.rest_api.main import app

    account = await _register(api_prefix, "settings-owner")
    headers = _auth(account)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        empty = await client.get(
            f"{api_prefix}/users/{account['user_id']}/settings", headers=headers
        )
        assert empty.status_code == 200
        assert empty.json() == {}

        stored = await client.put(
            f"{api_prefix}/users/{account['user_id']}/settings",
            json={"ui": {"fallbackChain": ["da", "sv", "en"]}},
            headers=headers,
        )
        assert stored.status_code == 200
        assert stored.json() == {"stored": True}

        fetched = await client.get(
            f"{api_prefix}/users/{account['user_id']}/settings", headers=headers
        )
        assert fetched.status_code == 200
        assert fetched.json() == {"ui": {"fallbackChain": ["da", "sv", "en"]}}


@pytest.mark.contract
@pytest.mark.asyncio
async def test_settings_of_another_user_forbidden(api_prefix: str) -> None:
    """Another account's settings are refused, unknown or not."""
    from models.rest_api.main import app

    owner = await _register(api_prefix, "settings-owner-2")
    other = await _register(api_prefix, "settings-other")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        get = await client.get(
            f"{api_prefix}/users/{owner['user_id']}/settings", headers=_auth(other)
        )
        assert get.status_code == 403

        put = await client.put(
            f"{api_prefix}/users/{owner['user_id']}/settings",
            json={"ui": {}},
            headers=_auth(other),
        )
        assert put.status_code == 403


@pytest.mark.contract
@pytest.mark.asyncio
async def test_settings_require_a_token(api_prefix: str) -> None:
    """Without a token there is no owner to check."""
    from models.rest_api.main import app

    account = await _register(api_prefix, "settings-owner-3")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        get = await client.get(f"{api_prefix}/users/{account['user_id']}/settings")
        assert get.status_code == 401

        put = await client.put(
            f"{api_prefix}/users/{account['user_id']}/settings", json={"ui": {}}
        )
        assert put.status_code == 401


@pytest.mark.contract
@pytest.mark.asyncio
async def test_settings_must_be_an_object(api_prefix: str) -> None:
    """A non-object body is rejected by request validation."""
    from models.rest_api.main import app

    account = await _register(api_prefix, "settings-owner-4")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        put = await client.put(
            f"{api_prefix}/users/{account['user_id']}/settings",
            json=["not", "an", "object"],
            headers=_auth(account),
        )
        assert put.status_code == 422
