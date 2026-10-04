"""Integration tests: a user may only act on their own account.

These endpoints take a user id in the path. Without an ownership check that id
is whatever the client says, so any caller could read or overwrite another
account's settings, toggle their watchlist, read their activity or delete the
account outright.
"""

import sys
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, "src")


async def register(client: AsyncClient, api_prefix: str) -> tuple[str, int]:
    """Register a fresh account and return its bearer token and user id."""
    response = await client.post(
        f"{api_prefix}/auth/register",
        json={
            "username": f"owner-{uuid.uuid4().hex[:12]}",
            "password": "e2e-password",
        },
    )
    assert response.status_code == 200
    body = response.json()
    return str(body["token"]), int(body["user_id"])


@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_reads_own_settings(api_prefix: str, initialized_app: None) -> None:
    """The owner can read their own settings."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        token, user_id = await register(client, api_prefix)
        headers = {"Authorization": f"Bearer {token}"}

        await client.put(
            f"{api_prefix}/users/{user_id}/settings",
            json={"ui": {"language": "sv"}},
            headers=headers,
        )

        response = await client.get(
            f"{api_prefix}/users/{user_id}/settings", headers=headers
        )

        assert response.status_code == 200
        assert response.json()["ui"]["language"] == "sv"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cannot_read_another_users_settings(
    api_prefix: str, initialized_app: None
) -> None:
    """Reading somebody else's settings is refused."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        victim_token, victim_id = await register(client, api_prefix)
        await client.put(
            f"{api_prefix}/users/{victim_id}/settings",
            json={"ui": {"language": "sv"}},
            headers={"Authorization": f"Bearer {victim_token}"},
        )
        attacker_token, _ = await register(client, api_prefix)

        response = await client.get(
            f"{api_prefix}/users/{victim_id}/settings",
            headers={"Authorization": f"Bearer {attacker_token}"},
        )

        assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cannot_overwrite_another_users_settings(
    api_prefix: str, initialized_app: None
) -> None:
    """Writing somebody else's settings is refused and changes nothing."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        victim_token, victim_id = await register(client, api_prefix)
        victim_headers = {"Authorization": f"Bearer {victim_token}"}
        await client.put(
            f"{api_prefix}/users/{victim_id}/settings",
            json={"ui": {"language": "sv"}},
            headers=victim_headers,
        )
        attacker_token, _ = await register(client, api_prefix)

        response = await client.put(
            f"{api_prefix}/users/{victim_id}/settings",
            json={"ui": {"language": "de"}},
            headers={"Authorization": f"Bearer {attacker_token}"},
        )

        assert response.status_code == 403
        # The victim's settings are untouched
        unchanged = await client.get(
            f"{api_prefix}/users/{victim_id}/settings", headers=victim_headers
        )
        assert unchanged.json()["ui"]["language"] == "sv"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_anonymous_settings_access_is_refused(
    api_prefix: str, initialized_app: None
) -> None:
    """Without a token there is no owner to check, so it is a 401."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, user_id = await register(client, api_prefix)

        read = await client.get(f"{api_prefix}/users/{user_id}/settings")
        write = await client.put(
            f"{api_prefix}/users/{user_id}/settings", json={"ui": {"language": "de"}}
        )

        assert read.status_code == 401
        assert write.status_code == 401


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cannot_delete_another_user(
    api_prefix: str, initialized_app: None
) -> None:
    """Deleting somebody else's account is refused."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, victim_id = await register(client, api_prefix)
        attacker_token, _ = await register(client, api_prefix)

        response = await client.delete(
            f"{api_prefix}/users/{victim_id}",
            headers={"Authorization": f"Bearer {attacker_token}"},
        )

        assert response.status_code == 403
        # The account is still there
        still_there = await client.get(f"{api_prefix}/users/{victim_id}")
        assert still_there.status_code == 200


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cannot_toggle_another_users_watchlist(
    api_prefix: str, initialized_app: None
) -> None:
    """Toggling somebody else's watchlist is refused."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, victim_id = await register(client, api_prefix)
        attacker_token, _ = await register(client, api_prefix)

        response = await client.put(
            f"{api_prefix}/users/{victim_id}/watchlist/toggle",
            json={"enabled": False},
            headers={"Authorization": f"Bearer {attacker_token}"},
        )

        assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cannot_read_another_users_activity(
    api_prefix: str, initialized_app: None
) -> None:
    """Reading somebody else's activity is refused."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, victim_id = await register(client, api_prefix)
        attacker_token, _ = await register(client, api_prefix)

        response = await client.get(
            f"{api_prefix}/users/{victim_id}/activity",
            headers={"Authorization": f"Bearer {attacker_token}"},
        )

        assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_reads_own_activity(api_prefix: str, initialized_app: None) -> None:
    """The ownership check does not lock users out of their own data."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        token, user_id = await register(client, api_prefix)

        response = await client.get(
            f"{api_prefix}/users/{user_id}/activity",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_can_delete_own_account(
    api_prefix: str, initialized_app: None
) -> None:
    """Self-deletion still works."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        token, user_id = await register(client, api_prefix)

        response = await client.delete(
            f"{api_prefix}/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        gone = await client.get(f"{api_prefix}/users/{user_id}")
        assert gone.status_code == 404
