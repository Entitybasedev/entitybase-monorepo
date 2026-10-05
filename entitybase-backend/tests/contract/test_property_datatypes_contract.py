"""Contract tests for property types and property creation."""

import sys

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, "src")


@pytest.mark.contract
@pytest.mark.asyncio
async def test_property_datatypes_lists_supported_types(api_prefix: str) -> None:
    """The endpoint describes every type the UI must render."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"{api_prefix}/property-datatypes")

    assert response.status_code == 200
    body = response.json()
    ids = [entry["id"] for entry in body["datatypes"]]
    assert ids == ["wikibase-item", "string"]
    # Each entry carries what a per-type form needs
    for entry in body["datatypes"]:
        assert entry["label"]
        assert entry["value_kind"] in {"entity", "text"}
        assert entry["value_label"]
        assert entry["value_placeholder"]


@pytest.mark.contract
@pytest.mark.asyncio
async def test_property_datatypes_item_is_entity_valued(api_prefix: str) -> None:
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"{api_prefix}/property-datatypes")

    entries = {e["id"]: e for e in response.json()["datatypes"]}
    assert entries["wikibase-item"]["value_kind"] == "entity"
    assert entries["string"]["value_kind"] == "text"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_create_property_stores_datatype_and_label(api_prefix: str) -> None:
    """The datatype and the label end up on the stored revision."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            f"{api_prefix}/entities/properties",
            json={
                "type": "property",
                "datatype": "string",
                "labels": {"en": {"language": "en", "value": "a string property"}},
            },
            headers={"X-Edit-Summary": "test", "X-User-ID": "0"},
        )
        assert created.status_code == 200
        property_id = created.json()["data"]["entity_id"]

        revision = await client.get(f"{api_prefix}/entities/{property_id}.json")

    assert revision.status_code == 200
    data = revision.json()["data"]
    assert data["datatype"] == "string"
    assert data["entity_type"] == "property"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_create_property_without_datatype_rejected(api_prefix: str) -> None:
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"{api_prefix}/entities/properties",
            json={"type": "property"},
            headers={"X-Edit-Summary": "test", "X-User-ID": "0"},
        )

    assert response.status_code == 400


@pytest.mark.contract
@pytest.mark.asyncio
async def test_create_property_with_unsupported_datatype_rejected(
    api_prefix: str,
) -> None:
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"{api_prefix}/entities/properties",
            json={"type": "property", "datatype": "external-id"},
            headers={"X-Edit-Summary": "test", "X-User-ID": "0"},
        )

    assert response.status_code == 400


@pytest.mark.contract
@pytest.mark.asyncio
async def test_create_property_rejects_non_property_type(api_prefix: str) -> None:
    """The endpoint only creates properties."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"{api_prefix}/entities/properties",
            json={"type": "item"},
            headers={"X-Edit-Summary": "test", "X-User-ID": "0"},
        )

    assert response.status_code == 400
