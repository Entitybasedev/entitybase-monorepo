"""Integration tests for the edit activity stats endpoint."""

import logging
import sys

sys.path.insert(0, "src")

import pytest
from httpx import ASGITransport, AsyncClient

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_edit_stats_response_schema(api_prefix: str) -> None:
    """The edit stats response contains the three counters."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"{api_prefix}/stats/edits")
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == {"edits_7d", "edits_30d", "edits_total"}
        assert all(isinstance(data[key], int) for key in data)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_edit_stats_counts_a_new_edit(api_prefix: str) -> None:
    """Creating an entity counts as an edit within the last 7/30 days."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"{api_prefix}/entities/items",
            headers={"X-Edit-Summary": "stats test", "X-User-ID": "0"},
        )
        assert response.status_code == 200

        response = await client.get(f"{api_prefix}/stats/edits")
        assert response.status_code == 200
        data = response.json()
        assert data["edits_7d"] >= 1
        assert data["edits_30d"] >= data["edits_7d"]
        assert data["edits_total"] >= data["edits_30d"]
