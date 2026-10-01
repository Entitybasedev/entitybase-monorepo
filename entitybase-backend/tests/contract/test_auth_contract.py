"""Contract tests for the authentication endpoints and middleware."""

import sys

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, "src")

from models.config.settings import settings


PASSWORD = "wonderland"


async def _register(api_prefix: str, username: str) -> dict:
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            f"{api_prefix}/auth/register",
            json={"username": username, "password": PASSWORD},
        )
        return res


async def _login(api_prefix: str, username: str, password: str = PASSWORD) -> dict:
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            f"{api_prefix}/auth/login",
            json={"username": username, "password": password},
        )
        return res


@pytest.mark.contract
@pytest.mark.asyncio
async def test_register_returns_token(api_prefix: str) -> None:
    res = await _register(api_prefix, "alice")
    assert res.status_code == 200
    body = res.json()
    assert body["token"].count(".") == 2
    assert body["user_id"] > 0
    assert body["username"] == "alice"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_register_duplicate_username_rejected(api_prefix: str) -> None:
    first = await _register(api_prefix, "bob")
    assert first.status_code == 200
    second = await _register(api_prefix, "bob")
    assert second.status_code == 400


@pytest.mark.contract
@pytest.mark.asyncio
async def test_login_returns_token(api_prefix: str) -> None:
    registered = (await _register(api_prefix, "carol")).json()
    res = await _login(api_prefix, "carol")
    assert res.status_code == 200
    body = res.json()
    assert body["user_id"] == registered["user_id"]
    assert body["token"].count(".") == 2


@pytest.mark.contract
@pytest.mark.asyncio
async def test_login_wrong_password_unauthorized(api_prefix: str) -> None:
    registered = await _register(api_prefix, "dave")
    assert registered.status_code == 200
    res = await _login(api_prefix, "dave", "wrong")
    assert res.status_code == 401


@pytest.mark.contract
@pytest.mark.asyncio
async def test_login_unknown_user_unauthorized(api_prefix: str) -> None:
    res = await _login(api_prefix, "nobody")
    assert res.status_code == 401


@pytest.mark.contract
@pytest.mark.asyncio
async def test_write_without_token_unauthorized_when_auth_enabled(
    api_prefix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "auth_secret", "test-secret")
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(f"{api_prefix}/users", json={"user_id": 90002})
        assert res.status_code == 401


@pytest.mark.contract
@pytest.mark.asyncio
async def test_write_with_token_allowed_when_auth_enabled(
    api_prefix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "auth_secret", "test-secret")
    body = (await _register(api_prefix, "erin")).json()
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            f"{api_prefix}/users",
            json={"user_id": body["user_id"]},
            headers={
                "Authorization": f"Bearer {body['token']}",
                "X-User-ID": str(body["user_id"]),
            },
        )
        assert res.status_code == 200


@pytest.mark.contract
@pytest.mark.asyncio
async def test_write_with_mismatched_user_id_forbidden(
    api_prefix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "auth_secret", "test-secret")
    body = (await _register(api_prefix, "frank")).json()
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            f"{api_prefix}/users",
            json={"user_id": 90010},
            headers={
                "Authorization": f"Bearer {body['token']}",
                "X-User-ID": "90010",
            },
        )
        assert res.status_code == 403


@pytest.mark.contract
@pytest.mark.asyncio
async def test_write_with_garbage_token_unauthorized(
    api_prefix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "auth_secret", "test-secret")
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            f"{api_prefix}/users",
            json={"user_id": 90011},
            headers={"Authorization": "Bearer not.a.token"},
        )
        assert res.status_code == 401


@pytest.mark.contract
@pytest.mark.asyncio
async def test_write_allowed_without_auth_when_secret_unset(
    api_prefix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "auth_secret", "")
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(f"{api_prefix}/users", json={"user_id": 90012})
        assert res.status_code == 200
