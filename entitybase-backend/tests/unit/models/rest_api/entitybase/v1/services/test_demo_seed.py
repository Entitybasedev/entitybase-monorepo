import logging
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, "src")

from models.rest_api.entitybase.v1.services.demo_seed import (
    DEMO_ENTITIES,
    seed_demo_entities,
)


def make_state(existing_ids: list[str] | None = None, listed: list[str] | None = None):
    """Build a state handler double whose instance looks empty by default."""
    db_client = MagicMock()
    db_client.entity_exists.side_effect = lambda entity_id: (
        entity_id in (existing_ids or [])
    )
    db_client.list_entities_by_type.return_value = listed if listed is not None else []
    state = MagicMock()
    state.db_client = db_client
    state.validator = MagicMock()
    return state


@pytest.fixture(autouse=True)
def patch_create_handler(monkeypatch):
    """Patch the create handler so no database work happens."""
    created: list[str] = []

    async def create_entity(request, **kwargs):
        created.append(request.id)
        if request.id == "Q1" and getattr(create_entity, "fail_q1", False):
            raise RuntimeError("boom")
        return MagicMock()

    create_entity.created = created  # type: ignore[attr-defined]
    create_entity.fail_q1 = False  # type: ignore[attr-defined]
    monkeypatch.setattr(
        "models.rest_api.entitybase.v1.services.demo_seed.EntityCreateHandler",
        MagicMock(return_value=MagicMock(create_entity=create_entity)),
    )
    return create_entity


class TestSeedDemoEntities:
    @pytest.mark.asyncio
    async def test_creates_item_property_and_lexeme(self, patch_create_handler):
        state = make_state()

        created = await seed_demo_entities(state)

        assert sorted(created) == ["L1", "P1", "Q1"]

    @pytest.mark.asyncio
    async def test_skips_when_instance_already_has_entities(self, patch_create_handler):
        state = make_state(listed=["Q300000001"])

        created = await seed_demo_entities(state)

        assert created == []
        assert patch_create_handler.created == []

    @pytest.mark.asyncio
    async def test_skips_existing_ids(self, patch_create_handler):
        state = make_state(existing_ids=["Q1"])

        created = await seed_demo_entities(state)

        assert "Q1" not in created
        assert "P1" in created

    @pytest.mark.asyncio
    async def test_one_failure_does_not_stop_the_rest(self, patch_create_handler):
        patch_create_handler.fail_q1 = True
        state = make_state()

        created = await seed_demo_entities(state)

        assert "Q1" not in created
        assert sorted(created) == ["L1", "P1"]

    @pytest.mark.asyncio
    async def test_skips_without_database_client(self, patch_create_handler):
        state = make_state()
        state.db_client = None

        assert await seed_demo_entities(state) == []

    def test_demo_entities_cover_all_three_types(self):
        types = {entity["type"] for entity in DEMO_ENTITIES}
        assert types == {"item", "property", "lexeme"}
        # The property must be seeded before the item that references it
        assert DEMO_ENTITIES[0]["id"] == "P1"
        assert "P1" in DEMO_ENTITIES[1]["claims"]
