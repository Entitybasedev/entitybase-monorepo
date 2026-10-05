"""Integration tests for property datatypes.

A property's type is stored on its revision and decides how values are entered,
so these tests cover the whole path: create with a type, read it back, and the
validation that keeps untyped properties out.
"""

import sys
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, "src")

HEADERS = {"X-Edit-Summary": "test", "X-User-ID": "0"}


async def create_property(client: AsyncClient, api_prefix: str, **body) -> str:
    """Create a property and return its id."""
    payload = {"type": "property", **body}
    response = await client.post(
        f"{api_prefix}/entities/properties", json=payload, headers=HEADERS
    )
    assert response.status_code == 200
    return str(response.json()["data"]["entity_id"])


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.parametrize("datatype", ["wikibase-item", "string"])
async def test_property_keeps_its_datatype(
    api_prefix: str, initialized_app: None, datatype: str
) -> None:
    """Each supported type can be created and read back."""
    from models.rest_api.main import app

    label = f"e2e {datatype} {uuid.uuid4().hex[:8]}"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        property_id = await create_property(
            client,
            api_prefix,
            datatype=datatype,
            labels={"en": {"language": "en", "value": label}},
        )
        assert property_id.startswith("P")

        revision = await client.get(f"{api_prefix}/entities/{property_id}.json")

    assert revision.status_code == 200
    data = revision.json()["data"]
    assert data["datatype"] == datatype
    assert data["entity_type"] == "property"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_property_label_is_stored(api_prefix: str, initialized_app: None) -> None:
    """The label sent with the property is kept, not dropped."""
    from models.rest_api.main import app

    label = f"e2e labelled {uuid.uuid4().hex[:8]}"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        property_id = await create_property(
            client,
            api_prefix,
            datatype="string",
            labels={"en": {"language": "en", "value": label}},
        )

        stored = await client.get(f"{api_prefix}/entities/{property_id}/labels/en")

    assert stored.status_code == 200
    assert stored.json()["value"] == label


@pytest.mark.asyncio
@pytest.mark.integration
async def test_property_without_datatype_is_rejected(
    api_prefix: str, initialized_app: None
) -> None:
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"{api_prefix}/entities/properties",
            json={"type": "property"},
            headers=HEADERS,
        )

    assert response.status_code == 400
    assert "requires a datatype" in response.json()["message"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_property_with_unsupported_datatype_is_rejected(
    api_prefix: str, initialized_app: None
) -> None:
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"{api_prefix}/entities/properties",
            json={"type": "property", "datatype": "commonsMedia"},
            headers=HEADERS,
        )

    assert response.status_code == 400
    assert "Unsupported datatype" in response.json()["message"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_item_with_datatype_is_rejected(
    api_prefix: str, initialized_app: None
) -> None:
    """A datatype on an item is a client mistake, not something to drop."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"{api_prefix}/entities/items",
            json={"type": "item", "datatype": "string"},
            headers=HEADERS,
        )

    assert response.status_code == 400


@pytest.mark.asyncio
@pytest.mark.integration
async def test_supported_datatypes_are_served(
    api_prefix: str, initialized_app: None
) -> None:
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"{api_prefix}/property-datatypes")

    assert response.status_code == 200
    assert [entry["id"] for entry in response.json()["datatypes"]] == [
        "wikibase-item",
        "string",
    ]
