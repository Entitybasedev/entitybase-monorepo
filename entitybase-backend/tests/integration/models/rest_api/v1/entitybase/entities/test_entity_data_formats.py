"""Integration tests for entity data formats (JSON, Turtle)."""

import logging

import pytest
from httpx import ASGITransport, AsyncClient

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_entity_data_json() -> None:
    """Test getting entity data in JSON format."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_response = await client.post(
            "/v1/entities/items",
            headers={"X-Edit-Summary": "create test entity", "X-User-ID": "0"},
        )
        assert create_response.status_code == 200
        entity_id = create_response.json()["data"]["entity_id"]

        await client.put(
            f"/v1/entities/{entity_id}/labels/en",
            json={"language": "en", "value": "Test Entity"},
            headers={"X-Edit-Summary": "add label", "X-User-ID": "0"},
        )

        response = await client.get(f"/v1/entities/{entity_id}.json")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == entity_id
        assert "labels" in data
        logger.info("✓ Entity JSON retrieval passed")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_entity_data_turtle() -> None:
    """Test getting entity data in Turtle format."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_response = await client.post(
            "/v1/entities/items",
            headers={"X-Edit-Summary": "create test entity", "X-User-ID": "0"},
        )
        assert create_response.status_code == 200
        entity_id = create_response.json()["data"]["entity_id"]

        response = await client.get(f"/v1/entities/{entity_id}.ttl")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/turtle"
        logger.info("✓ Entity Turtle retrieval passed")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_turtle_carries_the_terms_it_stores() -> None:
    """The Turtle carries the terms, not just the entity type.

    Terms are stored as content hashes, so an export that reads the stored
    revision directly emits an entity with no label, no description and no
    statement - and still answers 200. Assert the text is actually in the body.
    """
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_response = await client.post(
            "/v1/entities/items",
            headers={"X-Edit-Summary": "create test entity", "X-User-ID": "0"},
        )
        assert create_response.status_code == 200
        entity_id = create_response.json()["data"]["entity_id"]

        label_response = await client.put(
            f"/v1/entities/{entity_id}/labels/en",
            json={"language": "en", "value": "Turtle Label"},
            headers={"X-Edit-Summary": "add label", "X-User-ID": "0"},
        )
        assert label_response.status_code == 200

        description_response = await client.put(
            f"/v1/entities/{entity_id}/descriptions/en",
            json={"language": "en", "value": "Turtle Description"},
            headers={"X-Edit-Summary": "add description", "X-User-ID": "0"},
        )
        assert description_response.status_code == 200

        response = await client.get(f"/v1/entities/{entity_id}.ttl")
        assert response.status_code == 200
        turtle = response.text
        assert f'wd:{entity_id} rdfs:label "Turtle Label"@en' in turtle
        assert f'wd:{entity_id} schema:description "Turtle Description"@en' in turtle
        logger.info("✓ Entity Turtle carries its terms")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_turtle_types_an_entity_as_itself() -> None:
    """A property is typed as a Property, and a lexeme as a Lexeme."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        property_response = await client.post(
            "/v1/entities/properties",
            json={
                "type": "property",
                "datatype": "wikibase-item",
                "labels": {"en": {"language": "en", "value": "instance of"}},
            },
            headers={"X-Edit-Summary": "create property", "X-User-ID": "0"},
        )
        assert property_response.status_code == 200
        property_id = property_response.json()["data"]["entity_id"]
        assert (
            f"wd:{property_id} a wikibase:Property ."
            in (await client.get(f"/v1/entities/{property_id}.ttl")).text
        )

        lexeme_response = await client.post(
            "/v1/entities/lexemes",
            json={
                "type": "lexeme",
                "language": "Q1860",
                "lexicalCategory": "Q1084",
                "lemmas": {"en": {"language": "en", "value": "turtle"}},
            },
            headers={"X-Edit-Summary": "create lexeme", "X-User-ID": "0"},
        )
        assert lexeme_response.status_code == 200
        lexeme_id = lexeme_response.json()["id"]
        assert (
            f"wd:{lexeme_id} a wikibase:Lexeme ."
            in (await client.get(f"/v1/entities/{lexeme_id}.ttl")).text
        )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_entity_json_revision() -> None:
    """Test getting entity revision in JSON format."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_response = await client.post(
            "/v1/entities/items",
            headers={"X-Edit-Summary": "create test entity", "X-User-ID": "0"},
        )
        assert create_response.status_code == 200
        entity_id = create_response.json()["data"]["entity_id"]

        await client.put(
            f"/v1/entities/{entity_id}/labels/en",
            json={"language": "en", "value": "Test Entity"},
            headers={"X-Edit-Summary": "add label", "X-User-ID": "0"},
        )

        response = await client.get(f"/v1/entities/{entity_id}/revision/1/json")
        assert response.status_code == 200

        data = response.json()
        assert "labels" in data
        logger.info("✓ Entity JSON revision retrieval passed")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_entity_revision_not_found() -> None:
    """Test that non-existent revision returns 404."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_response = await client.post(
            "/v1/entities/items",
            headers={"X-Edit-Summary": "create test entity", "X-User-ID": "0"},
        )
        assert create_response.status_code == 200
        entity_id = create_response.json()["data"]["entity_id"]

        response = await client.get(f"/v1/entities/{entity_id}/revision/999/json")
        assert response.status_code == 404
        logger.info("✓ Non-existent revision returns 404")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_entity_json_revision_not_found() -> None:
    """Test that non-existent entity revision returns 404."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_response = await client.post(
            "/v1/entities/items",
            headers={"X-Edit-Summary": "create test entity", "X-User-ID": "0"},
        )
        assert create_response.status_code == 200
        entity_id = create_response.json()["data"]["entity_id"]

        response = await client.get(f"/v1/entities/{entity_id}/revision/999/ttl")
        assert response.status_code == 404
        logger.info("✓ Non-existent TTL revision returns 404")
