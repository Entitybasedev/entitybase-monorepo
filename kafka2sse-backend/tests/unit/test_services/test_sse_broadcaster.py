import pytest
import asyncio

from src.services.sse_broadcaster import SSEBroadcaster
from src.services.client_connection import ClientConnection
from src.models.sse_event import SSEEvent
from src.models.entity_change import EntityChange, ChangeType


class TestSSEBroadcaster:
    def test_format_sse_event(self):
        broadcaster = SSEBroadcaster()

        entity_data = EntityChange(
            entity_id="Q42",
            revision_id=12345,
            change_type=ChangeType.EDIT,
            from_revision_id=12344,
            changed_at="2023-01-01T12:00:00Z",
            edit_summary="Updated description",
            user_id="user1",
        )
        sse_event = SSEEvent(
            event_type="entity_change",
            id="82c5a9",
            data=entity_data,
        )

        formatted = broadcaster._format_sse_event(sse_event)

        assert "event: message" in formatted
        assert "id: 82c5a9" in formatted
        assert "data:" in formatted
        assert "entity_change" in formatted
        assert formatted.endswith("\n\n")

    def test_format_sse_event_creation(self):
        broadcaster = SSEBroadcaster()

        entity_data = EntityChange(
            entity_id="Q99",
            revision_id=1,
            change_type=ChangeType.CREATION,
            changed_at="2024-01-01T00:00:00Z",
            user_id="admin",
        )
        sse_event = SSEEvent(
            event_type="entity_change",
            id="abc123",
            data=entity_data,
        )

        formatted = broadcaster._format_sse_event(sse_event)

        assert "event: message" in formatted
        assert "id: abc123" in formatted

    def test_format_sse_event_deletion(self):
        broadcaster = SSEBroadcaster()

        entity_data = EntityChange(
            entity_id="Q100",
            revision_id=5,
            change_type=ChangeType.HARD_DELETE,
            changed_at="2024-06-01T12:00:00Z",
            user_id="admin",
        )
        sse_event = SSEEvent(
            event_type="entity_change",
            id="del1",
            data=entity_data,
        )

        formatted = broadcaster._format_sse_event(sse_event)

        assert "event: message" in formatted
        assert "hard_delete" in formatted


class TestSSEBroadcasterStream:
    @pytest.mark.asyncio
    async def test_stream_events_empty_queue(self):
        broadcaster = SSEBroadcaster()
        client = ClientConnection(queue_size=10)

        async def fake_unsubscribe(topic, client):
            pass

        async def run_stream():
            async for _ in broadcaster.stream_events(client, "test-topic", fake_unsubscribe):
                break

        await asyncio.wait_for(run_stream(), timeout=0.2)

    @pytest.mark.asyncio
    async def test_stream_events_with_disconnect(self):
        broadcaster = SSEBroadcaster()
        client = ClientConnection(queue_size=10)
        client.disconnected = True

        async def fake_unsubscribe(topic, client):
            pass

        async def run_stream():
            async for _ in broadcaster.stream_events(client, "test-topic", fake_unsubscribe):
                break

        await asyncio.wait_for(run_stream(), timeout=0.2)

    @pytest.mark.asyncio
    async def test_stream_events_with_limit(self):
        broadcaster = SSEBroadcaster()
        client = ClientConnection(queue_size=10)
        client.limit = 1
        
        entity_data = EntityChange(
            entity_id="Q1",
            revision_id=1,
            change_type=ChangeType.CREATION,
            changed_at="2024-01-01T00:00:00Z",
            user_id="user1",
        )
        event = SSEEvent(id="1", event_type="entity_change", data=entity_data)
        await client.queue.put(event)

        async def fake_unsubscribe(topic, client):
            pass

        events = []
        async for ev in broadcaster.stream_events(client, "test-topic", fake_unsubscribe):
            events.append(ev)
            if client.events_sent >= client.limit:
                break

        assert len(events) == 1