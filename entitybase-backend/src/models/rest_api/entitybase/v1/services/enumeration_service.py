"""Entity ID enumeration service.

Auto-assigns entity IDs using a simple database allocation: the next ID
for a prefix is MAX(existing numeric IDs for that prefix, floor) + 1.
Imported entities keep their original IDs and never touch this path.
"""

import logging
from typing import Any

from pydantic import BaseModel, Field

from models.rest_api.utils import raise_validation_error

logger = logging.getLogger(__name__)

# Minimum auto-assigned IDs to avoid collisions with imported Wikidata IDs
MIN_IDS = {
    "Q": 300_000_000,
    "P": 30_000,
    "L": 5_000_000,
    "E": 50_000,
}

TYPE_PREFIX = {
    "item": "Q",
    "property": "P",
    "lexeme": "L",
    "entityschema": "E",
}


class EnumerationService(BaseModel):
    """Service for auto-assigning entity IDs (imported entities use explicit IDs)."""

    db_client: Any

    def get_next_entity_id(self, entity_type: str) -> str:
        """Get the next available entity ID for the given entity type.

        Allocates MAX(existing numeric IDs for the prefix, floor) + 1.
        Concurrent creations that race on the same ID are settled by the
        unique primary key on entity_id_mapping when the creation
        transaction registers the entity.
        """
        prefix = TYPE_PREFIX.get(entity_type)
        if prefix is None:
            raise_validation_error(f"Unsupported entity type: {entity_type}")

        current_max = self.db_client.get_max_numeric_entity_id(prefix)
        floor = MIN_IDS.get(prefix, 1)
        next_number = max(current_max or 0, floor) + 1
        logger.debug(
            f"Allocated {prefix}{next_number} "
            f"(current_max={current_max}, floor={floor})"
        )
        return f"{prefix}{next_number}"

    def confirm_id_usage(self, entity_id: str) -> None:
        """Confirm that an auto-assigned ID has been used (no-op since the
        creation transaction registers the ID in entity_id_mapping)."""
        logger.debug(f"Confirmed usage of auto-assigned ID {entity_id}")
