"""Contract tests for the recent changes endpoint."""

import sys

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, "src")

HEADERS = {"X-Edit-Summary": "recent changes test"}


@pytest.mark.contract
@pytest.mark.asyncio
async def test_recent_changes_lists_creates_and_label_edits(
    api_prefix: str,
) -> None:
    """Creates and label edits show up with granular change types."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create = await client.post(
            f"{api_prefix}/entities/items",
            headers={**HEADERS, "X-User-ID": "90001"},
        )
        assert create.status_code == 200
        entity_id = create.json()["data"]["entity_id"]

        label = await client.put(
            f"{api_prefix}/entities/{entity_id}/labels/en",
            json={"language": "en", "value": "Recent"},
            headers={**HEADERS, "X-User-ID": "90001"},
        )
        assert label.status_code == 200

        res = await client.get(f"{api_prefix}/recentchanges")
        assert res.status_code == 200
        entries = res.json()
        assert isinstance(entries, list)
        assert len(entries) >= 2

        # Newest first
        assert entries[0]["change_type"] == "label_update"
        assert entries[0]["entity_id"] == entity_id
        assert entries[0]["edit_summary"] == "recent changes test"
        assert entries[0]["user_id"] == 90001

        types = [entry["change_type"] for entry in entries]
        assert "entity_create" in types


@pytest.mark.contract
@pytest.mark.asyncio
async def test_recent_changes_change_type_filter(api_prefix: str) -> None:
    """The change_type query parameter filters entries."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.get(
            f"{api_prefix}/recentchanges",
            params={"change_type": "label_update"},
        )
        assert res.status_code == 200
        for entry in res.json():
            assert entry["change_type"] == "label_update"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_recent_changes_invalid_filter_rejected(api_prefix: str) -> None:
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.get(
            f"{api_prefix}/recentchanges",
            params={"change_type": "nonsense"},
        )
        assert res.status_code == 400


@pytest.mark.contract
@pytest.mark.asyncio
async def test_import_shows_as_import_with_import_user(api_prefix: str) -> None:
    """Imports are tagged entity_import and attributed to user 0."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            f"{api_prefix}/import",
            json={
                "type": "item",
                "id": "Q90010",
                "labels": {"en": {"language": "en", "value": "Imported"}},
            },
        )
        assert res.status_code == 200

        recent = await client.get(f"{api_prefix}/recentchanges")
        assert recent.status_code == 200
        entries = recent.json()
        imports = [e for e in entries if e["change_type"] == "entity_import"]
        assert imports, "import entry missing from recent changes"
        assert imports[0]["user_id"] == 0
        assert imports[0]["entity_id"] == "Q90010"
        assert imports[0]["edit_summary"] == "Bulk import"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_recent_changes_exclude_imports(api_prefix: str) -> None:
    """exclude_imports=true hides import entries but keeps normal edits."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create = await client.post(
            f"{api_prefix}/entities/items",
            headers={"X-User-ID": "90001", "X-Edit-Summary": "human edit"},
        )
        assert create.status_code == 200
        entity_id = create.json()["data"]["entity_id"]
        await client.post(
            f"{api_prefix}/import",
            json={"type": "item", "id": "Q90011"},
        )

        res = await client.get(
            f"{api_prefix}/recentchanges", params={"exclude_imports": True}
        )
        assert res.status_code == 200
        entries = res.json()
        assert all(e["change_type"] != "entity_import" for e in entries)
        assert any(
            e["entity_id"] == entity_id and e["change_type"] == "entity_create"
            for e in entries
        )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_recent_changes_pagination(api_prefix: str) -> None:
    """Limit and offset paginate the list."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        full = await client.get(f"{api_prefix}/recentchanges", params={"limit": 3})
        assert full.status_code == 200
        page1 = full.json()

        page2_res = await client.get(
            f"{api_prefix}/recentchanges", params={"limit": 3, "offset": 3}
        )
        assert page2_res.status_code == 200
        page2 = page2_res.json()

        if len(page1) == 3 and page2:
            ids_page1 = {entry["id"] for entry in page1}
            ids_page2 = {entry["id"] for entry in page2}
            assert not ids_page1 & ids_page2
