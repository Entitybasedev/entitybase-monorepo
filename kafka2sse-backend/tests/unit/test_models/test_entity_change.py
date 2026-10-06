import pytest
from pydantic import ValidationError

from src.models.entity_change import ChangeType, EntityChange
from src.models.sse_event import SSEEvent


class TestEntityChange:
    def test_valid_entity_change(self):
        data = {
            "entity_id": "Q42",
            "revision_id": 12345,
            "change_type": "edit",
            "from_revision_id": 12344,
            "changed_at": "2023-01-01T12:00:00Z",
            "edit_summary": "Updated description",
            "user_id": "user1",
        }
        entity = EntityChange(**data)
        assert entity.entity_id == "Q42"
        assert entity.revision_id == 12345
        assert entity.change_type == ChangeType.EDIT
        assert entity.from_revision_id == 12344

    def test_default_values(self):
        data = {
            "entity_id": "Q42",
            "revision_id": 12345,
            "change_type": "edit",
            "changed_at": "2023-01-01T12:00:00Z",
            "user_id": "user1",
        }
        entity = EntityChange(**data)
        assert entity.from_revision_id == 0
        assert entity.edit_summary == ""

    def test_invalid_change_type(self):
        data = {
            "entity_id": "Q42",
            "revision_id": 12345,
            "change_type": "invalid_type",
            "changed_at": "2023-01-01T12:00:00Z",
            "user_id": "user1",
        }
        with pytest.raises(ValidationError):
            EntityChange(**data)

    def test_negative_revision_id(self):
        data = {
            "entity_id": "Q42",
            "revision_id": -1,
            "change_type": "edit",
            "changed_at": "2023-01-01T12:00:00Z",
            "user_id": "user1",
        }
        with pytest.raises(ValidationError):
            EntityChange(**data)

    def test_zero_revision_id(self):
        data = {
            "entity_id": "Q42",
            "revision_id": 0,
            "change_type": "edit",
            "changed_at": "2023-01-01T12:00:00Z",
            "user_id": "user1",
        }
        with pytest.raises(ValidationError):
            EntityChange(**data)

    def test_alias_fields(self):
        entity = EntityChange(
            id="Q42",
            rev=12345,
            type=ChangeType.EDIT,
            from_rev=12344,
            at="2023-01-01T12:00:00Z",
            summary="Updated",
            user="user1",
        )
        assert entity.entity_id == "Q42"
        assert entity.revision_id == 12345


class TestSSEEvent:
    def test_valid_sse_event(self):
        data = {
            "event_type": "entity_change",
            "id": "82c5a9",
            "data": {
                "entity_id": "Q42",
                "revision_id": 12345,
                "change_type": "edit",
                "changed_at": "2023-01-01T12:00:00Z",
                "user_id": "user1",
            },
        }
        sse = SSEEvent(**data)
        assert sse.event_type == "entity_change"
        assert sse.id == "82c5a9"
        # data is the payload as a dict, whatever schema it follows
        assert sse.data["entity_id"] == "Q42"

    def test_event_type_is_not_restricted(self):
        """Any event type is allowed.

        This gateway serves several topics, each with its own payload schema,
        and they name themselves. Restricting the type to "entity_change"
        rejected everything on any other topic - as a warning, in an empty
        stream, rather than as an error.
        """
        data = {
            "event_type": "incremental_rdf_diff",
            "id": "82c5a9",
            "data": {"entity_id": "P1", "operation": "import"},
        }
        sse = SSEEvent(**data)
        assert sse.event_type == "incremental_rdf_diff"
        assert sse.data["operation"] == "import"

    def test_data_may_be_a_model(self):
        """A payload model is accepted and stored as a dict."""
        sse = SSEEvent(
            id="1",
            event_type="entity_change",
            data=EntityChange(
                entity_id="Q1",
                revision_id=1,
                change_type=ChangeType.CREATION,
                changed_at="2024-01-01T00:00:00Z",
                user_id="user1",
            ),
        )
        assert sse.data["entity_id"] == "Q1"


class TestChangeType:
    def test_all_change_types(self):
        assert ChangeType.CREATION.value == "creation"
        assert ChangeType.EDIT.value == "edit"
        assert ChangeType.REDIRECT.value == "redirect"
        assert ChangeType.UNREDIRECT.value == "unredirect"
        assert ChangeType.ARCHIVAL.value == "archival"
        assert ChangeType.UNARCHIVAL.value == "unarchival"
        assert ChangeType.LOCK.value == "lock"
        assert ChangeType.UNLOCK.value == "unlock"
        assert ChangeType.SOFT_DELETE.value == "soft_delete"
        assert ChangeType.HARD_DELETE.value == "hard_delete"