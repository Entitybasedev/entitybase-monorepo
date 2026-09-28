"""Contract tests for GET /health.

Asserts response shape conformance: status codes and required fields.
"""

import pytest
from confluent_kafka import KafkaException
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
@pytest.mark.contract
async def test_health_returns_200_with_required_fields(mock_producer) -> None:
    from src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200

    body = response.json()
    assert set(body.keys()) >= {"status", "kafka", "backend_type"}
    assert body["status"] in {"ok", "degraded"}
    assert body["kafka"] in {"connected", "disconnected"}
    assert isinstance(body["backend_type"], str)


@pytest.mark.asyncio
@pytest.mark.contract
async def test_health_connected_when_broker_reachable(mock_producer) -> None:
    from src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["kafka"] == "connected"


@pytest.mark.asyncio
@pytest.mark.contract
async def test_health_degraded_when_broker_unreachable() -> None:
    from unittest.mock import MagicMock, patch

    from src.main import app

    with patch("src.main.Producer") as producer_cls:
        producer = MagicMock()
        producer.list_topics.side_effect = KafkaException("broker down")
        producer_cls.return_value = producer

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "degraded"
    assert body["kafka"] == "disconnected"
