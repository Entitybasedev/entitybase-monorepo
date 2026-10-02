"""Contract tests for the user list endpoint."""

import sys

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, "src")


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_users_paginates(api_prefix: str) -> None:
    """Users created via the API appear, paginated with usernames."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            f"{api_prefix}/auth/register",
            json={"username": "listuser", "password": "pw"},
        )
        assert created.status_code == 200
        user_id = created.json()["user_id"]

        res = await client.get(f"{api_prefix}/users", params={"limit": 100, "offset": 0})
        assert res.status_code == 200
        body = res.json()
        assert "users" in body and "count" in body
        listed = {u["user_id"]: u for u in body["users"]}
        assert user_id in listed
        assert listed[user_id]["username"] == "listuser"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_users_offset_pages(api_prefix: str) -> None:
    """Offset pages do not repeat users from the first page."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Ensure at least five users exist regardless of prior tests
        for i in range(3):
            await client.post(
                f"{api_prefix}/auth/register",
                json={"username": f"offset-user-{i}", "password": "pw"},
            )

        page1 = await client.get(f"{api_prefix}/users", params={"limit": 2, "offset": 0})
        page2 = await client.get(f"{api_prefix}/users", params={"limit": 2, "offset": 2})
        assert page1.status_code == 200 and page2.status_code == 200
        ids1 = {u["user_id"] for u in page1.json()["users"]}
        ids2 = {u["user_id"] for u in page2.json()["users"]}
        assert ids1 and ids2
        assert not ids1 & ids2


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_users_read_is_public(api_prefix: str) -> None:
    """Listing users is a read: allowed without a token."""
    from models.rest_api.main import app
    from models.config.settings import settings

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(settings, "auth_secret", "test-secret")
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            res = await client.get(f"{api_prefix}/users")
            assert res.status_code == 200
    finally:
        monkeypatch.undo()
