"""Unit tests for enumeration_service."""

import pytest

from models.rest_api.entitybase.v1.services.enumeration_service import (
    MIN_IDS,
    EnumerationService,
)


class FakeDbClient:
    """Fake db client returning a configured max numeric ID."""

    def __init__(self, max_by_prefix: dict[str, int] | None = None):
        self.max_by_prefix = max_by_prefix or {}
        self.queried: list[str] = []

    def get_max_numeric_entity_id(self, prefix: str) -> int:
        self.queried.append(prefix)
        return self.max_by_prefix.get(prefix, 0)


@pytest.fixture
def service() -> EnumerationService:
    return EnumerationService(db_client=FakeDbClient())


class TestGetNextEntityId:
    def test_uses_floor_when_no_entities_exist(self, service) -> None:
        assert service.get_next_entity_id("item") == "Q300000001"

    def test_uses_floor_per_prefix(self, service) -> None:
        assert service.get_next_entity_id("property") == "P30001"
        assert service.get_next_entity_id("lexeme") == "L5000001"

    def test_allocates_above_current_max_when_max_exceeds_floor(self) -> None:
        db = FakeDbClient({"Q": 300_500_000})
        service = EnumerationService(db_client=db)
        assert service.get_next_entity_id("item") == "Q300500001"

    def test_floor_wins_over_imported_ids(self) -> None:
        db = FakeDbClient({"Q": 300_500})
        service = EnumerationService(db_client=db)
        assert service.get_next_entity_id("item") == "Q300000001"

    def test_max_is_queried_per_prefix(self, service) -> None:
        service.get_next_entity_id("item")
        assert service.db_client.queried == ["Q"]

    def test_unsupported_entity_type_raises(self, service) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            service.get_next_entity_id("nonsense")


class TestMinIds:
    def test_floors_match_documented_values(self) -> None:
        assert MIN_IDS["Q"] == 300_000_000
        assert MIN_IDS["P"] == 30_000
        assert MIN_IDS["L"] == 5_000_000
        assert MIN_IDS["E"] == 50_000
