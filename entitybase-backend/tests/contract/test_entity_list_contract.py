"""Contract tests for the entity list endpoint."""

import sys

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, "src")

HEADERS = {"X-User-ID": "90001", "X-Edit-Summary": "entity list test"}


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_entities_filters_by_type_and_paginates(
    api_prefix: str,
) -> None:
    """Items created in the test are listed; type filter excludes others."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        item = await client.post(f"{api_prefix}/entities/items", headers=HEADERS)
        assert item.status_code == 200
        item_id = item.json()["data"]["entity_id"]

        listed = await client.get(
            f"{api_prefix}/entities",
            params={"entity_type": "item", "limit": 10, "offset": 0},
        )
        assert listed.status_code == 200
        body = listed.json()
        assert "entities" in body and "count" in body
        ids = [e["entity_id"] for e in body["entities"]]
        assert item_id in ids
        for entry in body["entities"]:
            assert entry["entity_id"].startswith("Q")
            assert entry["head_revision_id"] >= 1


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_entities_property_type(api_prefix: str) -> None:
    """Property listing only contains P-prefixed entities."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        prop = await client.post(
            f"{api_prefix}/entities/properties",
            json={"type": "property", "datatype": "wikibase-item"},
            headers=HEADERS,
        )
        assert prop.status_code == 200
        prop_id = prop.json()["data"]["entity_id"]

        listed = await client.get(
            f"{api_prefix}/entities",
            params={"entity_type": "property", "limit": 10, "offset": 0},
        )
        assert listed.status_code == 200
        ids = [e["entity_id"] for e in listed.json()["entities"]]
        assert prop_id in ids
        for entity_id in ids:
            assert entity_id.startswith("P")


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_entities_requires_type_filter(api_prefix: str) -> None:
    """Without any filter the endpoint rejects the request."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.get(f"{api_prefix}/entities")
        assert res.status_code == 400


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_entities_pagination_offsets(api_prefix: str) -> None:
    """Offset pages do not repeat entries from the first page."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        for _ in range(3):
            await client.post(f"{api_prefix}/entities/items", headers=HEADERS)

        page1 = await client.get(
            f"{api_prefix}/entities", params={"entity_type": "item", "limit": 2}
        )
        page2 = await client.get(
            f"{api_prefix}/entities",
            params={"entity_type": "item", "limit": 2, "offset": 2},
        )
        assert page1.status_code == 200 and page2.status_code == 200
        ids1 = {e["entity_id"] for e in page1.json()["entities"]}
        ids2 = {e["entity_id"] for e in page2.json()["entities"]}
        assert ids1 and ids2
        assert not ids1 & ids2
