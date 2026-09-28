"""Fuzz/edge-case contract tests.

Malformed or hostile input must produce 404/422 client errors,
never an unhandled 500.
"""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
@pytest.mark.contract
async def test_metadata_invalid_topic_characters_return_404(mock_consumer) -> None:
    from src.main import app

    for topic in ["../etc/passwd", "topic%00null", "topic with spaces"]:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/v1/streams/{topic}/metadata")
        assert response.status_code in {404, 422}, (
            f"{topic!r} -> {response.status_code}"
        )


@pytest.mark.asyncio
@pytest.mark.contract
async def test_stream_unknown_topic_returns_404(mock_producer) -> None:
    from httpx import ASGITransport as T
    from httpx import AsyncClient as C

    from src.main import app

    async with C(transport=T(app=app), base_url="http://test") as client:
        response = await client.get("/v1/streams/no_such_topic")
    assert response.status_code == 404
    assert "no_such_topic" in response.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.contract
async def test_stream_invalid_offset_returns_422(mock_consumer) -> None:
    from src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/v1/streams/entity_change", params={"offset": "not-an-int"}
        )
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.contract
async def test_stream_invalid_limit_returns_422(mock_consumer) -> None:
    from src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/v1/streams/entity_change", params={"limit": "many"}
        )
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.contract
async def test_unknown_route_returns_404() -> None:
    from src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/definitely/not/a/route")
    assert response.status_code == 404
