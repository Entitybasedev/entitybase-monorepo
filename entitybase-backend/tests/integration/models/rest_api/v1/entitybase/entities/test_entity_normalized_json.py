"""Integration tests for the normalized JSON endpoint (/entities/{id}.njson)."""

import logging

import pytest
from httpx import ASGITransport, AsyncClient

logger = logging.getLogger(__name__)

HEADERS = {"X-Edit-Summary": "njson test", "X-User-ID": "0"}


async def _create_item(client: AsyncClient) -> str:
    response = await client.post("/v1/entities/items", headers=HEADERS)
    assert response.status_code == 200
    entity_id: str = response.json()["data"]["entity_id"]
    return entity_id


@pytest.mark.asyncio
@pytest.mark.integration
async def test_normalized_json_resolves_labels_and_descriptions() -> None:
    """Terms come back as their text, not as content hashes."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        entity_id = await _create_item(client)
        await client.put(
            f"/v1/entities/{entity_id}/labels/en",
            json={"language": "en", "value": "Douglas Adams"},
            headers=HEADERS,
        )
        await client.put(
            f"/v1/entities/{entity_id}/descriptions/en",
            json={"language": "en", "value": "English author"},
            headers=HEADERS,
        )
        await client.put(
            f"/v1/entities/{entity_id}/aliases/en",
            json=["Douglas Noel Adams"],
            headers=HEADERS,
        )

        response = await client.get(f"/v1/entities/{entity_id}.njson")
        assert response.status_code == 200

        data = response.json()["data"]
        assert data["id"] == entity_id
        assert data["labels"]["en"]["value"] == "Douglas Adams"
        assert data["descriptions"]["en"]["value"] == "English author"
        assert data["aliases"]["en"][0]["value"] == "Douglas Noel Adams"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_normalized_json_does_not_expose_hashes() -> None:
    """No content hash and no hash index appears anywhere in the response."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        entity_id = await _create_item(client)
        await client.put(
            f"/v1/entities/{entity_id}/labels/en",
            json={"language": "en", "value": "Douglas Adams"},
            headers=HEADERS,
        )

        revision = (
            await client.get(f"/v1/entities/{entity_id}.json")
        ).json()["data"]
        label_hash = revision["hashes"]["labels"]["en"]

        response = await client.get(f"/v1/entities/{entity_id}.njson")
        assert response.status_code == 200

        body = response.json()["data"]
        assert "hashes" not in body
        assert str(label_hash) not in str(body)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_normalized_json_resolves_statements() -> None:
    """Statements come back as their stored object, with the value inline."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        property_response = await client.post(
            "/v1/entities/properties",
            json={"type": "property", "datatype": "wikibase-item"},
            headers=HEADERS,
        )
        assert property_response.status_code == 200
        property_id = property_response.json()["data"]["entity_id"]

        entity_id = await _create_item(client)
        await client.put(
            f"/v1/entities/{entity_id}/labels/en",
            json={"language": "en", "value": "Douglas Adams"},
            headers=HEADERS,
        )
        subject_id = await _create_item(client)

        statement = await client.post(
            f"/v1/entities/{entity_id}/statements/{property_id}",
            json={
                "snaktype": "value",
                "property": property_id,
                "datatype": "wikibase-item",
                "datavalue": {"value": {"id": subject_id}, "type": "wikibase-item"},
            },
            headers=HEADERS,
        )
        assert statement.status_code == 200

        response = await client.get(f"/v1/entities/{entity_id}.njson")
        assert response.status_code == 200

        statements = response.json()["data"]["statements"]
        assert len(statements) == 1
        assert statements[0]["mainsnak"]["property"] == property_id
        assert (
            statements[0]["mainsnak"]["datavalue"]["value"]["id"] == subject_id
        )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_normalized_json_matches_the_json_endpoint() -> None:
    """The two endpoints describe the same entity: same fields, hashes resolved.

    Compared as parsed JSON. The only intended difference is that .njson
    resolves the hash index that .json exposes.
    """
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        property_response = await client.post(
            "/v1/entities/properties",
            json={"type": "property", "datatype": "string"},
            headers=HEADERS,
        )
        property_id = property_response.json()["data"]["entity_id"]

        entity_id = await _create_item(client)
        await client.put(
            f"/v1/entities/{entity_id}/labels/en",
            json={"language": "en", "value": "Douglas Adams"},
            headers=HEADERS,
        )
        await client.put(
            f"/v1/entities/{entity_id}/labels/sv",
            json={"language": "sv", "value": "Douglas Adams"},
            headers=HEADERS,
        )
        await client.put(
            f"/v1/entities/{entity_id}/descriptions/en",
            json={"language": "en", "value": "English author"},
            headers=HEADERS,
        )
        await client.put(
            f"/v1/entities/{entity_id}/aliases/en",
            json=["Douglas Noel Adams", "DNA"],
            headers=HEADERS,
        )
        subject_id = await _create_item(client)
        await client.post(
            f"/v1/entities/{entity_id}/statements/{property_id}",
            json={
                "snaktype": "value",
                "property": property_id,
                "datatype": "string",
                "datavalue": {"value": "a value", "type": "string"},
            },
            headers=HEADERS,
        )
        await client.post(
            f"/v1/entities/{entity_id}/sitelinks/enwiki",
            json={"site": "enwiki", "title": "Douglas Adams"},
            headers=HEADERS,
        )

        revision = (await client.get(f"/v1/entities/{entity_id}.json")).json()["data"]
        normalized = (
            await client.get(f"/v1/entities/{entity_id}.njson")
        ).json()["data"]

        # Every field that is not a hash reference is identical
        for field in (
            "revision_id",
            "entity_type",
            "datatype",
            "properties",
            "property_counts",
            "state",
            "edit",
            "created_at",
            "schema_version",
            "redirects_to",
        ):
            assert normalized.get(field) == revision.get(field), (
                f"{field} differs between .json and .njson"
            )

        # The resolved values correspond to the hashes .json points at
        assert normalized["labels"]["en"]["value"] == "Douglas Adams"
        assert normalized["labels"]["sv"]["value"] == "Douglas Adams"
        assert normalized["descriptions"]["en"]["value"] == "English author"
        assert [a["value"] for a in normalized["aliases"]["en"]] == [
            "Douglas Noel Adams",
            "DNA",
        ]
        assert normalized["sitelinks"]["enwiki"]["title"] == "Douglas Adams"
        assert len(normalized["statements"]) == len(revision["hashes"]["statements"])
        assert normalized["statements"][0]["mainsnak"]["datavalue"]["value"] == "a value"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_normalized_json_resolves_repeated_content_once() -> None:
    """Two languages with the same label text both resolve, from one lookup."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        entity_id = await _create_item(client)
        for language in ("en", "sv", "da"):
            await client.put(
                f"/v1/entities/{entity_id}/labels/{language}",
                json={"language": language, "value": "Douglas Adams"},
                headers=HEADERS,
            )

        response = await client.get(f"/v1/entities/{entity_id}.njson")
        assert response.status_code == 200

        labels = response.json()["data"]["labels"]
        assert {lang: term["value"] for lang, term in labels.items()} == {
            "en": "Douglas Adams",
            "sv": "Douglas Adams",
            "da": "Douglas Adams",
        }


@pytest.mark.asyncio
@pytest.mark.integration
async def test_normalized_json_property_keeps_its_datatype() -> None:
    """A property's datatype is part of the document, not a hash reference."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/entities/properties",
            json={"type": "property", "datatype": "string"},
            headers=HEADERS,
        )
        property_id = response.json()["data"]["entity_id"]
        await client.put(
            f"/v1/entities/{property_id}/labels/en",
            json={"language": "en", "value": "instance of"},
            headers=HEADERS,
        )

        data = (
            await client.get(f"/v1/entities/{property_id}.njson")
        ).json()["data"]

        assert data["entity_type"] == "property"
        assert data["datatype"] == "string"
        assert data["labels"]["en"]["value"] == "instance of"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_normalized_json_empty_entity() -> None:
    """An entity with nothing stored returns empty collections, not an error."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        entity_id = await _create_item(client)

        response = await client.get(f"/v1/entities/{entity_id}.njson")
        assert response.status_code == 200

        data = response.json()["data"]
        assert data["labels"] == {}
        assert data["descriptions"] == {}
        assert data["aliases"] == {}
        assert data["sitelinks"] == {}
        assert data["statements"] == []


@pytest.mark.asyncio
@pytest.mark.integration
async def test_normalized_json_missing_entity() -> None:
    """A missing entity is a 404, like on the .json endpoint."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/entities/Q999999999.njson")
        assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.integration
async def test_normalized_json_invalid_identifier() -> None:
    """An unusable identifier is rejected, like on the .json endpoint."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/entities/not-an-id.njson")
        assert response.status_code == 400