"""Integration tests for the per-language all-terms endpoint."""

import logging
import sys

sys.path.insert(0, "src")

import pytest
from httpx import ASGITransport, AsyncClient

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_entity_terms_rejects_batched_or_invalid_entity_id(
    api_prefix: str,
) -> None:
    """The endpoint accepts only a single QID or PID (no batches, no other IDs)."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        for entity_id in ["Q1,Q2", "XYZ", "Q", "L42", "q1"]:
            response = await client.get(f"{api_prefix}/entities/{entity_id}/terms/en")
            assert response.status_code == 422, entity_id


@pytest.mark.asyncio
@pytest.mark.integration
async def test_entity_terms_rejects_batched_language(api_prefix: str) -> None:
    """The endpoint accepts only a single language code."""
    from models.rest_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"{api_prefix}/entities/Q1/terms/en,sv")
        assert response.status_code == 422
