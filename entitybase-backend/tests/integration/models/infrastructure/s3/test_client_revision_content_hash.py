"""Integration tests for revision reads via content hash.

Revision storage lives in MariaDB: the entity->revision->content_hash
mapping is resolved from entity_revisions and the payload is loaded
from entity_revision_data. These tests exercise that flow through
StateHandler.read_revision_data, the same entry point the API uses.
"""

import pytest
from fastapi import HTTPException

from models.config.settings import settings
from models.data.infrastructure.s3.enums import EntityType, EditType, EditData
from models.data.infrastructure.s3.hashes.hash_maps import HashMaps
from models.data.infrastructure.s3.entity_state import EntityState
from models.data.infrastructure.s3.revision_data import S3RevisionData
from models.infrastructure.db.repositories.revision_data import (
    RevisionDataRepository,
)
from models.infrastructure.s3.revision.revision_data import RevisionData


def create_minimal_revision_data(entity_id: str, revision_id: int) -> RevisionData:
    """Create minimal revision data for testing."""
    return RevisionData(
        revision_id=revision_id,
        entity_type=EntityType.ITEM,
        edit=EditData(
            type=EditType.MANUAL_UPDATE,
            user_id=0,
            mass=False,
            summary="Test",
            at="2025-01-01T00:00:00Z",
        ),
        hashes=HashMaps(),
        schema_version="4.0.0",
        created_at="2025-01-01T00:00:00Z",
        redirects_to="",
        state=EntityState(),
        property_counts=None,
        properties=[],
    )


def store_revision_data(
    db_client, entity_id: str, revision_id: int, content_hash: int
) -> None:
    """Store a revision payload in entity_revision_data."""
    entity_data = create_minimal_revision_data(entity_id, revision_id)
    s3_revision_data = S3RevisionData(
        schema="4.0.0",
        revision=entity_data.model_dump(),
        hash=content_hash,
        created_at="2025-01-01T00:00:00Z",
    )
    RevisionDataRepository(db_client=db_client).store(
        content_hash, s3_revision_data.model_dump()
    )
    db_client.insert_revision(
        entity_id=entity_id,
        revision_id=revision_id,
        entity_data=entity_data,
        content_hash=content_hash,
    )


@pytest.fixture
def state_handler():
    """Real StateHandler wired to the test database via settings."""
    from models.rest_api.entitybase.v1.handlers.state import StateHandler

    return StateHandler(settings=settings)


class TestRevisionReadWithContentHash:
    """Integration tests for revision reading with content hash."""

    def test_read_revision_queries_database_first(self, db_client, state_handler):
        """Test that read_revision resolves the content hash from the database."""
        entity_id = "Q123"
        revision_id = 1
        content_hash = 123456789

        db_client.register_entity(entity_id)
        store_revision_data(db_client, entity_id, revision_id, content_hash)

        result = state_handler.read_revision_data(
            entity_id=entity_id, revision_id=revision_id
        )

        assert result is not None
        assert result.revision["revision_id"] == revision_id

    def test_read_revision_entity_not_found(self, state_handler):
        """Test that read_revision raises error for non-existent entity."""
        with pytest.raises(HTTPException):
            state_handler.read_revision_data(entity_id="Q999", revision_id=1)

    def test_read_revision_revision_not_found(self, db_client, state_handler):
        """Test that read_revision raises error for non-existent revision."""
        entity_id = "Q123"

        db_client.register_entity(entity_id)

        with pytest.raises(HTTPException):
            state_handler.read_revision_data(entity_id=entity_id, revision_id=999)

    def test_read_revision_end_to_end(self, db_client, state_handler):
        """Test end-to-end revision read operation."""
        entity_id = "Q456"
        revision_id = 2
        content_hash = 987654321

        db_client.register_entity(entity_id)
        store_revision_data(db_client, entity_id, revision_id, content_hash)

        result = state_handler.read_revision_data(
            entity_id=entity_id, revision_id=revision_id
        )

        assert result is not None
        assert result.revision["revision_id"] == revision_id
        assert result.revision["entity_type"] == "item"
