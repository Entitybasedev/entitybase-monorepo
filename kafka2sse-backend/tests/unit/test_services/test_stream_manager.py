import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from src.services.stream_manager import StreamManager, ClientConnection


@patch("src.services.stream_manager.redis_state")
class TestStreamManagerInit:
    def test_init(self, mock_redis):
        manager = StreamManager()
        assert manager._topics == {}
        assert len(manager._worker_id) == 8

    def test_get_topics_empty(self, mock_redis):
        manager = StreamManager()
        assert manager.get_topics() == []

    def test_get_topics_with_topics(self, mock_redis):
        manager = StreamManager()
        mock_consumer = MagicMock()
        manager._topics["topic1"] = mock_consumer
        manager._topics["topic2"] = mock_consumer
        topics = manager.get_topics()
        assert "topic1" in topics
        assert "topic2" in topics

    def test_clients_dict_type(self, mock_redis):
        manager = StreamManager()
        assert isinstance(manager._clients, dict)


@patch("src.services.stream_manager.redis_state")
@patch("src.services.stream_manager.KafkaConsumerService")
class TestStreamManagerSubscribe:
    @pytest.mark.asyncio
    async def test_subscribe(self, mock_kafka, mock_redis):
        mock_redis.register_consumer = AsyncMock()
        mock_redis.increment_client_count = AsyncMock()
        
        mock_kafka_instance = MagicMock()
        mock_kafka_instance.start = MagicMock()
        mock_kafka.return_value = mock_kafka_instance
        
        manager = StreamManager()
        client = await manager.subscribe("test-topic")
        
        assert client is not None

    @pytest.mark.asyncio
    async def test_subscribe_with_limit(self, mock_kafka, mock_redis):
        mock_redis.register_consumer = AsyncMock()
        mock_redis.increment_client_count = AsyncMock()
        
        mock_kafka_instance = MagicMock()
        mock_kafka_instance.start = MagicMock()
        mock_kafka.return_value = mock_kafka_instance
        
        manager = StreamManager()
        client = await manager.subscribe("test-topic", limit=10)
        
        assert client.limit == 10

    @pytest.mark.asyncio
    async def test_subscribe_with_offset(self, mock_kafka, mock_redis):
        mock_redis.register_consumer = AsyncMock()
        mock_redis.increment_client_count = AsyncMock()
        
        mock_kafka_instance = MagicMock()
        mock_kafka_instance.start = MagicMock()
        mock_kafka.return_value = mock_kafka_instance
        
        manager = StreamManager()
        client = await manager.subscribe("test-topic", offset=100)
        
        assert client is not None

    @pytest.mark.asyncio
    async def test_subscribe_with_since(self, mock_kafka, mock_redis):
        mock_redis.register_consumer = AsyncMock()
        mock_redis.increment_client_count = AsyncMock()
        
        mock_kafka_instance = MagicMock()
        mock_kafka_instance.start = MagicMock()
        mock_kafka.return_value = mock_kafka_instance
        
        manager = StreamManager()
        client = await manager.subscribe("test-topic", since="2024-01-01T00:00:00Z")
        
        assert client is not None

    @pytest.mark.asyncio
    async def test_subscribe_timeout(self, mock_kafka, mock_redis):
        mock_redis.register_consumer = AsyncMock()
        
        manager = StreamManager()
        
        import asyncio
        manager._lock = asyncio.Lock()
        async def fake_acquire():
            await asyncio.sleep(0)
            raise asyncio.TimeoutError()
        
        manager._lock.acquire = fake_acquire
        
        with pytest.raises(asyncio.TimeoutError):
            await manager.subscribe("test-topic")


@patch("src.services.stream_manager.redis_state")
class TestStreamManagerUnsubscribe:
    @pytest.mark.asyncio
    async def test_unsubscribe_removes_client(self, mock_redis):
        mock_redis.decrement_client_count = AsyncMock()
        mock_redis.unregister_consumer = AsyncMock()
        
        manager = StreamManager()
        client = ClientConnection()
        manager._clients["test-topic"].add(client)
        mock_consumer = MagicMock()
        mock_consumer.stop = AsyncMock()
        manager._topics["test-topic"] = mock_consumer
        
        await manager.unsubscribe("test-topic", client)
        
        assert client.disconnected

    @pytest.mark.asyncio
    async def test_unsubscribe_stops_consumer_when_empty(self, mock_redis):
        mock_redis.decrement_client_count = AsyncMock()
        mock_redis.unregister_consumer = AsyncMock()
        
        manager = StreamManager()
        client = ClientConnection()
        manager._clients["test-topic"].add(client)
        mock_consumer = AsyncMock()
        manager._topics["test-topic"] = mock_consumer
        
        await manager.unsubscribe("test-topic", client)
        
        mock_consumer.stop.assert_called_once()
        assert "test-topic" not in manager._topics


@patch("src.services.stream_manager.redis_state")
class TestStreamManagerRouteEvent:
    @pytest.mark.asyncio
    async def test_route_event(self, mock_redis):
        from src.models.sse_event import SSEEvent
        from src.models.entity_change import EntityChange, ChangeType
        
        manager = StreamManager()
        client = ClientConnection()
        manager._clients["test-topic"].add(client)
        
        entity = EntityChange(
            entity_id="Q1", revision_id=1, change_type=ChangeType.CREATION,
            changed_at="2024-01-01T00:00:00Z", user_id="user1"
        )
        event = SSEEvent(id="1", event_type="entity_change", data=entity)
        
        manager._route_event("test-topic", event)
        
        assert client.queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_route_event_disconnected_client(self, mock_redis):
        from src.models.sse_event import SSEEvent
        from src.models.entity_change import EntityChange, ChangeType
        
        manager = StreamManager()
        client = ClientConnection()
        client.disconnected = True
        manager._clients["test-topic"].add(client)
        
        entity = EntityChange(
            entity_id="Q1", revision_id=1, change_type=ChangeType.CREATION,
            changed_at="2024-01-01T00:00:00Z", user_id="user1"
        )
        event = SSEEvent(id="1", event_type="entity_change", data=entity)
        
        manager._route_event("test-topic", event)
        
        assert client.queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_route_event_queue_full(self, mock_redis):
        import asyncio
        from src.models.sse_event import SSEEvent
        from src.models.entity_change import EntityChange, ChangeType
        
        manager = StreamManager()
        client = ClientConnection(queue_size=1)
        client.queue.put_nowait = MagicMock(side_effect=[asyncio.QueueFull(), None])
        client.queue.get_nowait = MagicMock()
        manager._clients["test-topic"].add(client)
        
        entity = EntityChange(
            entity_id="Q1", revision_id=1, change_type=ChangeType.CREATION,
            changed_at="2024-01-01T00:00:00Z", user_id="user1"
        )
        event = SSEEvent(id="1", event_type="entity_change", data=entity)
        
        manager._route_event("test-topic", event)
        client.queue.get_nowait.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_event_queue_empty_after_full(self, mock_redis):
        import asyncio
        from src.models.sse_event import SSEEvent
        from src.models.entity_change import EntityChange, ChangeType
        
        manager = StreamManager()
        client = ClientConnection(queue_size=1)
        client.queue.put_nowait = MagicMock(side_effect=asyncio.QueueFull())
        client.queue.get_nowait = MagicMock(side_effect=asyncio.QueueEmpty())
        manager._clients["test-topic"].add(client)
        
        entity = EntityChange(
            entity_id="Q1", revision_id=1, change_type=ChangeType.CREATION,
            changed_at="2024-01-01T00:00:00Z", user_id="user1"
        )
        event = SSEEvent(id="1", event_type="entity_change", data=entity)
        
        manager._route_event("test-topic", event)

    @pytest.mark.asyncio
    async def test_route_event_no_clients(self, mock_redis):
        from src.models.sse_event import SSEEvent
        from src.models.entity_change import EntityChange, ChangeType
        
        manager = StreamManager()
        
        entity = EntityChange(
            entity_id="Q1", revision_id=1, change_type=ChangeType.CREATION,
            changed_at="2024-01-01T00:00:00Z", user_id="user1"
        )
        event = SSEEvent(id="1", event_type="entity_change", data=entity)
        
        manager._route_event("test-topic", event)

    @pytest.mark.asyncio
    async def test_route_event_queue_full_then_empty(self, mock_redis):
        import asyncio
        from src.models.sse_event import SSEEvent
        from src.models.entity_change import EntityChange, ChangeType
        
        manager = StreamManager()
        client = ClientConnection(queue_size=1)
        
        call_count = [0]
        def put_nowait_side_effect(event):
            call_count[0] += 1
            if call_count[0] == 1:
                raise asyncio.QueueFull()
        
        client.queue.put_nowait = MagicMock(side_effect=put_nowait_side_effect)
        client.queue.get_nowait = MagicMock(side_effect=asyncio.QueueEmpty())
        manager._clients["test-topic"].add(client)
        
        entity = EntityChange(
            entity_id="Q1", revision_id=1, change_type=ChangeType.CREATION,
            changed_at="2024-01-01T00:00:00Z", user_id="user1"
        )
        event = SSEEvent(id="1", event_type="entity_change", data=entity)
        
        manager._route_event("test-topic", event)
    
    @pytest.mark.asyncio
    async def test_route_event_multiple_clients(self, mock_redis):
        from src.models.sse_event import SSEEvent
        from src.models.entity_change import EntityChange, ChangeType
        
        manager = StreamManager()
        client1 = ClientConnection()
        client2 = ClientConnection()
        manager._clients["test-topic"].add(client1)
        manager._clients["test-topic"].add(client2)
        
        entity = EntityChange(
            entity_id="Q1", revision_id=1, change_type=ChangeType.CREATION,
            changed_at="2024-01-01T00:00:00Z", user_id="user1"
        )
        event = SSEEvent(id="1", event_type="entity_change", data=entity)
        
        manager._route_event("test-topic", event)
        
        assert client1.queue.qsize() == 1
        assert client2.queue.qsize() == 1
    
    @pytest.mark.asyncio
    async def test_route_event_disconnected_skipped(self, mock_redis):
        from src.models.sse_event import SSEEvent
        from src.models.entity_change import EntityChange, ChangeType
        
        manager = StreamManager()
        client1 = ClientConnection()
        client1.disconnected = True
        client2 = ClientConnection()
        manager._clients["test-topic"].add(client1)
        manager._clients["test-topic"].add(client2)
        
        entity = EntityChange(
            entity_id="Q1", revision_id=1, change_type=ChangeType.CREATION,
            changed_at="2024-01-01T00:00:00Z", user_id="user1"
        )
        event = SSEEvent(id="1", event_type="entity_change", data=entity)
        
        manager._route_event("test-topic", event)
        
        assert client1.queue.qsize() == 0
        assert client2.queue.qsize() == 1


@patch("src.services.stream_manager.redis_state")
class TestStreamManagerShutdown:
    @pytest.mark.asyncio
    async def test_shutdown(self, mock_redis):
        mock_redis.unregister_consumer = AsyncMock()
        
        manager = StreamManager()
        mock_consumer1 = AsyncMock()
        mock_consumer2 = AsyncMock()
        manager._topics["topic1"] = mock_consumer1
        manager._topics["topic2"] = mock_consumer2
        
        await manager.shutdown()
        
        mock_consumer1.stop.assert_called_once()
        mock_consumer2.stop.assert_called_once()
        assert len(manager._topics) == 0
        assert len(manager._clients) == 0


@patch("src.services.stream_manager.redis_state")
class TestStreamManagerMetadata:
    @pytest.mark.asyncio
    async def test_get_topic_metadata_no_workers(self, mock_redis):
        mock_redis.get_worker_count = AsyncMock(return_value=0)
        
        manager = StreamManager()
        
        result = await manager.get_topic_metadata("nonexistent-topic")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_topic_metadata_with_worker(self, mock_redis):
        mock_redis.get_worker_count = AsyncMock(return_value=1)
        mock_redis.get_client_count = AsyncMock(return_value=5)
        
        manager = StreamManager()
        manager._topics["test-topic"] = MagicMock()
        
        with patch.object(manager, "_get_watermark_offsets", return_value=(0, 100)):
            result = await manager.get_topic_metadata("test-topic")
        
        assert result is not None
        assert result["connected_clients"] == 5


class TestClientConnection:
    def test_client_connection_basic(self):
        client = ClientConnection()
        assert client.queue.maxsize == 100
        assert client.events_sent == 0

    def test_client_connection_custom_queue_size(self):
        client = ClientConnection(queue_size=50)
        assert client.queue.maxsize == 50

    def test_client_disconnected_flag(self):
        client = ClientConnection()
        assert not client.disconnected
        client.disconnected = True
        assert client.disconnected

    def test_client_id_format(self):
        client = ClientConnection()
        assert len(client.id) == 8

    def test_client_limit_default_none(self):
        client = ClientConnection()
        assert client.limit is None

    def test_client_limit_set(self):
        client = ClientConnection()
        client.limit = 10
        assert client.limit == 10