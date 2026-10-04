import sys

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, "src")

PASSWORD = "e2e-password"


async def _registered_account(
    client: AsyncClient, api_prefix: str, username: str
) -> tuple[int, dict[str, str]]:
    """Register an account and return its user id with auth headers.

    Disabling a watchlist acts on one account's data, so it needs that
    account's token; a bare X-User-ID header is not an identity.
    """
    response = await client.post(
        f"{api_prefix}/auth/register",
        json={"username": username, "password": PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    headers = {
        "Authorization": f"Bearer {body['token']}",
        "X-Edit-Summary": "test",
    }
    return int(body["user_id"]), headers


async def _disable_watchlist(
    client: AsyncClient, api_prefix: str, user_id: int, headers: dict[str, str]
) -> None:
    """Disable a watchlist, asserting that it took effect.

    Without this assertion a rejected toggle leaves the watchlist enabled and
    whatever depends on it being disabled fails somewhere else entirely.
    """
    response = await client.put(
        f"{api_prefix}/users/{user_id}/watchlist/toggle",
        json={"enabled": False},
        headers=headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.integration
async def test_add_watch(api_prefix: str, initialized_app: None) -> None:
    """Test adding a watch"""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        headers = {"X-Edit-Summary": "test", "X-User-ID": "0"}

        # Create entity first
        response = await client.post(
            f"{api_prefix}/entities/items",
            headers=headers,
        )
        assert response.status_code == 200
        entity_id = response.json()["data"]["entity_id"]

        # Register user
        await client.post(
            f"{api_prefix}/users",
            json={"user_id": 12345},
            headers={"X-Edit-Summary": "test", "X-User-ID": "0"},
        )

        # Add watch
        response = await client.post(
            f"{api_prefix}/users/12345/watchlist",
            json={"entity_id": entity_id, "properties": ["P31"]},
            headers={"X-Edit-Summary": "test", "X-User-ID": "0"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Watch added"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_add_watch_user_not_registered(
    api_prefix: str, initialized_app: None
) -> None:
    """Test adding a watch for unregistered user"""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"{api_prefix}/users/99999/watchlist",
            json={"entity_id": "Q42", "properties": ["P31"]},
            headers={"X-Edit-Summary": "test", "X-User-ID": "0"},
        )
        assert response.status_code == 404
        assert "User not registered" in response.json()["message"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_remove_watch(api_prefix: str, initialized_app: None) -> None:
    """Test removing a watch"""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        headers = {"X-Edit-Summary": "test", "X-User-ID": "0"}

        # Create entity first
        response = await client.post(
            f"{api_prefix}/entities/items",
            headers=headers,
        )
        assert response.status_code == 200
        entity_id = response.json()["data"]["entity_id"]

        # Register user and add watch
        await client.post(
            f"{api_prefix}/users",
            json={"user_id": 12345},
            headers={"X-Edit-Summary": "test", "X-User-ID": "0"},
        )
        await client.post(
            f"{api_prefix}/users/12345/watchlist",
            json={"entity_id": entity_id, "properties": ["P31"]},
            headers={"X-Edit-Summary": "test", "X-User-ID": "0"},
        )

        # Remove watch
        response = await client.post(
            f"{api_prefix}/users/12345/watchlist/remove",
            json={"entity_id": entity_id, "properties": ["P31"]},
            headers={"X-Edit-Summary": "test", "X-User-ID": "0"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Watch removed"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_watchlist(api_prefix: str, initialized_app: None) -> None:
    """Test getting user's watchlist"""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        headers = {"X-Edit-Summary": "test", "X-User-ID": "0"}

        # Create entity first
        response = await client.post(
            f"{api_prefix}/entities/items",
            headers=headers,
        )
        assert response.status_code == 200
        entity_id = response.json()["data"]["entity_id"]

        # Register user and add watch
        await client.post(
            f"{api_prefix}/users",
            json={"user_id": 12345},
            headers={"X-Edit-Summary": "test", "X-User-ID": "0"},
        )
        await client.post(
            f"{api_prefix}/users/12345/watchlist",
            json={"entity_id": entity_id, "properties": ["P31"]},
            headers={"X-Edit-Summary": "test", "X-User-ID": "0"},
        )

        # Get watchlist
        response = await client.get(f"{api_prefix}/users/12345/watchlist")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == 12345
        assert len(data["watches"]) == 1
        assert data["watches"][0]["entity_id"] == entity_id
        assert data["watches"][0]["properties"] == ["P31"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_watchlist_user_not_registered(
    api_prefix: str, initialized_app: None
) -> None:
    """Test getting watchlist for unregistered user"""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"{api_prefix}/users/99999/watchlist")
        assert response.status_code == 404
        assert "User not registered" in response.json()["message"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_remove_watch_by_id(api_prefix: str, initialized_app: None) -> None:
    """Test removing a watch by ID"""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        headers = {"X-Edit-Summary": "test", "X-User-ID": "0"}

        # Create entity first
        response = await client.post(
            f"{api_prefix}/entities/items",
            headers=headers,
        )
        assert response.status_code == 200
        entity_id = response.json()["data"]["entity_id"]

        # Register user and add watch
        await client.post(
            f"{api_prefix}/users",
            json={"user_id": 12345},
            headers={"X-Edit-Summary": "test", "X-User-ID": "0"},
        )
        await client.post(
            f"{api_prefix}/users/12345/watchlist",
            json={"entity_id": entity_id, "properties": ["P31"]},
            headers={"X-Edit-Summary": "test", "X-User-ID": "0"},
        )

        # Get watchlist to obtain the watch ID
        response = await client.get(f"{api_prefix}/users/12345/watchlist")
        assert response.status_code == 200
        data = response.json()
        watch_id = data["watches"][0]["id"]

        # Remove watch by ID
        response = await client.delete(
            f"{api_prefix}/users/12345/watchlist/{watch_id}",
            headers={"X-Edit-Summary": "test", "X-User-ID": "0"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Watch removed"

        # Verify watch is removed
        response = await client.get(f"{api_prefix}/users/12345/watchlist")
        assert response.status_code == 200
        data = response.json()
        assert len(data["watches"]) == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_notifications(api_prefix: str, initialized_app: None) -> None:
    """Test getting user notifications"""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Register user
        await client.post(
            f"{api_prefix}/users",
            json={"user_id": 12345},
            headers={"X-Edit-Summary": "test", "X-User-ID": "0"},
        )

        # Get notifications (should be empty initially)
        response = await client.get(f"{api_prefix}/users/12345/watchlist/notifications")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == 12345
        assert data["notifications"] == []


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_notifications_user_not_registered(
    api_prefix: str, initialized_app: None
) -> None:
    """Test getting notifications for unregistered user"""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"{api_prefix}/users/99999/watchlist/notifications")
        assert response.status_code == 404
        assert "User not registered" in response.json()["message"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mark_notification_checked(
    api_prefix: str, initialized_app: None
) -> None:
    """Test marking notification as checked"""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Register user
        await client.post(
            f"{api_prefix}/users",
            json={"user_id": 12345},
            headers={"X-Edit-Summary": "test", "X-User-ID": "0"},
        )

        # Mark notification checked (even if doesn't exist, should not error)
        response = await client.put(
            f"{api_prefix}/users/12345/watchlist/notifications/1/check",
            headers={"X-Edit-Summary": "test", "X-User-ID": "0"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Notification marked as checked"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_watchlist_stats_unregistered_user(
    api_prefix: str, initialized_app: None
) -> None:
    """Test getting watchlist stats for unregistered user returns 0 counts."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # For unregistered users, it returns 0 counts (not 404)
        response = await client.get(f"{api_prefix}/users/99999/watchlist/stats")
        assert response.status_code == 200
        data = response.json()
        assert "entity_count" in data
        assert "property_count" in data
        assert data["entity_count"] == 0
        assert data["property_count"] == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_watchlist_user_disabled(
    api_prefix: str, initialized_app: None
) -> None:
    """Test getting watchlist when watchlist is disabled returns 400."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        user_id, headers = await _registered_account(
            client, api_prefix, "watchlist-get-disabled"
        )

        # Disable watchlist
        await _disable_watchlist(client, api_prefix, user_id, headers)

        # Try to get watchlist when disabled
        response = await client.get(f"{api_prefix}/users/{user_id}/watchlist")
        assert response.status_code == 400
        assert "disabled" in response.json()["message"].lower()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_add_watch_disabled_user(api_prefix: str, initialized_app: None) -> None:
    """Test adding watch for user with disabled watchlist returns 400."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        user_id, headers = await _registered_account(
            client, api_prefix, "watchlist-add-disabled"
        )

        # Disable watchlist
        await _disable_watchlist(client, api_prefix, user_id, headers)

        # Try to add watch when disabled
        response = await client.post(
            f"{api_prefix}/users/{user_id}/watchlist",
            json={"entity_id": "Q42", "properties": ["P31"]},
            headers=headers,
        )
        assert response.status_code == 400
        assert "disabled" in response.json()["message"].lower()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_notifications_disabled_user(
    api_prefix: str, initialized_app: None
) -> None:
    """Test getting notifications when watchlist is disabled returns 400."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        user_id, headers = await _registered_account(
            client, api_prefix, "watchlist-notifications-disabled"
        )

        # Disable watchlist
        await _disable_watchlist(client, api_prefix, user_id, headers)

        # Try to get notifications when disabled
        response = await client.get(
            f"{api_prefix}/users/{user_id}/watchlist/notifications"
        )
        assert response.status_code == 400
        assert "disabled" in response.json()["message"].lower()
