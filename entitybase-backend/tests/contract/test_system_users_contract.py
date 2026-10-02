"""Contract tests for the startup-seeded system users."""

import sys

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, "src")


@pytest.mark.contract
@pytest.mark.asyncio
async def test_demo_user_can_login(api_prefix: str) -> None:
    """After _ensure_demo_user runs, demo/demo logs in and edits work."""
    from models.rest_api.main import _ensure_demo_user, app

    state = app.state.state_handler
    _ensure_demo_user(state)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            f"{api_prefix}/auth/login",
            json={"username": "demo", "password": "demo"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["user_id"] > 0

        # The token allows writes for that user
        write = await client.post(
            f"{api_prefix}/entities/items",
            headers={
                "Authorization": f"Bearer {body['token']}",
                "X-Edit-Summary": "demo write",
            },
        )
        assert write.status_code == 200


@pytest.mark.contract
@pytest.mark.asyncio
async def test_demo_user_seeding_is_idempotent(api_prefix: str) -> None:
    """Running the seeding twice keeps one demo account."""
    from models.rest_api.main import _ensure_demo_user, app

    state = app.state.state_handler
    _ensure_demo_user(state)
    _ensure_demo_user(state)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.get(f"{api_prefix}/users", params={"limit": 100})
        assert res.status_code == 200
        demos = [u for u in res.json()["users"] if u["username"] == "demo"]
        assert len(demos) == 1


@pytest.mark.contract
@pytest.mark.asyncio
async def test_import_user_exists_without_login(api_prefix: str) -> None:
    """The import user is labeled but cannot log in (no password)."""
    from models.rest_api.main import _ensure_import_user, app
    from models.config.settings import settings

    state = app.state.state_handler
    _ensure_import_user(state)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        login = await client.post(
            f"{api_prefix}/auth/login",
            json={"username": settings.import_username, "password": "anything"},
        )
        assert login.status_code == 401
