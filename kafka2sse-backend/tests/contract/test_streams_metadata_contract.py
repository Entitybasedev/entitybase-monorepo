"""Contract tests for GET /v1/streams/{topic}/metadata."""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
@pytest.mark.contract
async def test_metadata_returns_200_with_required_fields(mock_consumer) -> None:
    from src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/streams/entity_change/metadata")
    assert response.status_code == 200

    body = response.json()
    assert set(body.keys()) >= {
        "topic",
        "earliest_offset",
        "latest_offset",
        "message_count",
    }
    assert body["topic"] == "entity_change"
    assert body["earliest_offset"] == 0
    assert body["latest_offset"] == 5
    assert body["message_count"] == 5


@pytest.mark.asyncio
@pytest.mark.contract
async def test_metadata_unknown_topic_returns_404(mock_consumer) -> None:
    from src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/streams/no_such_topic/metadata")
    assert response.status_code == 404
    assert "no_such_topic" in response.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.contract
async def test_metadata_broker_error_returns_503(mock_consumer) -> None:
    from src.main import app

    mock_consumer.list_topics.side_effect = RuntimeError("connection refused")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/streams/entity_change/metadata")
    assert response.status_code == 503
