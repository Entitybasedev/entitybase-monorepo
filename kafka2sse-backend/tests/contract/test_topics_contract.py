"""Contract tests for GET /v1/topics."""

import pytest

from httpx import ASGITransport, AsyncClient

from tests.contract.conftest import make_cluster_metadata


@pytest.mark.asyncio
@pytest.mark.contract
async def test_topics_returns_200_with_list_of_strings(mock_producer) -> None:
    from src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/topics")
    assert response.status_code == 200

    body = response.json()
    assert set(body.keys()) == {"topics"}
    assert isinstance(body["topics"], list)
    assert all(isinstance(t, str) for t in body["topics"])


@pytest.mark.asyncio
@pytest.mark.contract
async def test_topics_excludes_internal_topics(mock_producer) -> None:
    from src.main import app

    mock_producer.list_topics.return_value = make_cluster_metadata(
        {
            "entity_change": 1,
            "entity_diff": 1,
            "__consumer_offsets": 50,
            "_schemas": 1,
        }
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/topics")
    assert response.status_code == 200

    topics = response.json()["topics"]
    assert "entity_change" in topics
    assert "entity_diff" in topics
    assert all(not t.startswith("_") for t in topics)


@pytest.mark.asyncio
@pytest.mark.contract
async def test_topics_sorted_and_deduplicated(mock_producer) -> None:
    from src.main import app

    mock_producer.list_topics.return_value = make_cluster_metadata(
        {"b_topic": 1, "a_topic": 1}
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/topics")
    assert response.status_code == 200

    assert response.json()["topics"] == ["a_topic", "b_topic"]


@pytest.mark.asyncio
@pytest.mark.contract
async def test_topics_empty_when_broker_unreachable(mock_producer, kafka_transport_error) -> None:
    from src.main import app

    mock_producer.list_topics.side_effect = kafka_transport_error

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/topics")
    assert response.status_code == 200

    assert response.json()["topics"] == []
