"""Seed a small demo dataset so a fresh instance is not empty.

Enabled with DEMO_SEED_ENABLED (set for the docker demo stack). The
entities go through the same import path as the POST /v1/import endpoint,
so a seeded entity looks exactly like an imported one.
"""

import logging
from typing import Any

from models.data.rest_api.v1.entitybase.request import (
    EntityChangeType,
    EntityCreateRequest,
)
from models.data.rest_api.v1.entitybase.request.headers import EditHeaders
from models.rest_api.entitybase.v1.handlers.entity.create import EntityCreateHandler
from models.rest_api.entitybase.v1.handlers.state import StateHandler

logger = logging.getLogger(__name__)

# The property comes first: the demo item references it.
DEMO_ENTITIES: tuple[dict[str, Any], ...] = (
    {
        "id": "P1",
        "type": "property",
        "datatype": "wikibase-item",
        "labels": {"en": {"language": "en", "value": "demo property"}},
        "descriptions": {
            "en": {"language": "en", "value": "Property seeded on startup."}
        },
    },
    {
        "id": "Q1",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Demo item"}},
        "descriptions": {"en": {"language": "en", "value": "Item seeded on startup."}},
        "aliases": {"en": [{"language": "en", "value": "demo entity"}]},
        "claims": {
            "P1": [
                {
                    "id": "demo-claim",
                    "type": "statement",
                    "rank": "normal",
                    "mainsnak": {
                        "snaktype": "value",
                        "property": "P1",
                        "datavalue": {"value": "seeded", "type": "string"},
                    },
                }
            ]
        },
    },
    {
        "id": "L1",
        "type": "lexeme",
        "lemmas": {"en": {"language": "en", "value": "demo"}},
        "language": "Q1860",
        "lexical_category": "Q1084",
    },
)


def _instance_is_empty(state: StateHandler) -> bool:
    """Whether the instance holds no entities yet.

    Only an empty instance is seeded, so a loaded instance (for example a
    Wikidata dump) never gets demo data mixed into it.
    """
    db_client = state.db_client
    if db_client is None:
        return False
    for entity_type in ("item", "property", "lexeme"):
        if db_client.list_entities_by_type(entity_type, limit=1):
            return False
    return True


async def seed_demo_entities(state: StateHandler) -> list[str]:
    """Import the demo entities, skipping any that already exist.

    Returns the IDs that were created. Failures are logged and never block
    startup, so a seeding problem cannot take the API down.
    """
    db_client = state.db_client
    if db_client is None:
        logger.warning("Demo seed skipped: database client not available")
        return []

    if not _instance_is_empty(state):
        logger.debug("Demo seed skipped: instance already has entities")
        return []

    handler = EntityCreateHandler(state=state)
    edit_headers = EditHeaders.model_validate(
        {"X-User-ID": 0, "X-Edit-Summary": "Demo seed"}
    )
    created: list[str] = []
    for payload in DEMO_ENTITIES:
        try:
            request = EntityCreateRequest.model_validate(payload)
            if db_client.entity_exists(request.id):
                logger.debug(f"Demo seed skipping existing entity {request.id}")
                continue
            await handler.create_entity(
                request,
                edit_headers=edit_headers,
                validator=state.validator,
                auto_assign_id=False,
                change_type=EntityChangeType.ENTITY_IMPORT,
            )
            created.append(request.id)
            logger.info(f"Seeded demo entity {request.id}")
        except Exception as e:
            logger.warning(
                f"Could not seed demo entity {payload.get('id')}: "
                f"{type(e).__name__}: {e}"
            )
    if created:
        logger.info(f"Demo seed created: {', '.join(created)}")
    return created
