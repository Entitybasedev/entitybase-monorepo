import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.services.client_connection import ClientConnection
from src.services.event_router import EventRouter


class TestClientConnection:
    def test_client_connection_creation(self):
        client = ClientConnection(queue_size=50)
        assert client.queue.maxsize == 50
        assert client.events_sent == 0
        assert client.limit is None
        assert not client.disconnected

    def test_client_connection_with_limit(self):
        client = ClientConnection(queue_size=100)
        client.limit = 10
        assert client.limit == 10

    def test_client_id_format(self):
        client = ClientConnection()
        assert len(client.id) == 8

    def test_default_queue_size(self):
        client = ClientConnection()
        assert client.queue.maxsize == 100


class TestEventRouter:
    def test_route_event(self):
        from src.models.sse_event import SSEEvent
        from src.models.entity_change import EntityChange

        mock_callback = MagicMock()
        router = EventRouter(mock_callback)

        entity = EntityChange(
            entity_id="Q42",
            revision_id=12345,
            change_type="edit",
            changed_at="2023-01-01T12:00:00Z",
            user_id="user1"
        )
        event = SSEEvent(
            event_type="entity_change",
            id="1",
            data=entity
        )

        router.route("test-topic", event)

        mock_callback.assert_called_once_with("test-topic", event)

    def test_route_event_exception(self):
        from src.models.sse_event import SSEEvent
        from src.models.entity_change import EntityChange

        def failing_callback(topic, event):
            raise Exception("test error")

        router = EventRouter(failing_callback)

        entity = EntityChange(
            entity_id="Q42",
            revision_id=12345,
            change_type="edit",
            changed_at="2023-01-01T12:00:00Z",
            user_id="user1"
        )
        event = SSEEvent(
            event_type="entity_change",
            id="1",
            data=entity
        )

        router.route("test-topic", event)