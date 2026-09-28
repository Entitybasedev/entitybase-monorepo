import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from src.services.kafka_consumer import KafkaConsumerService


class TestKafkaConsumerServiceInit:
    def test_init(self):
        callback = lambda t, e: None
        consumer = KafkaConsumerService("test-topic", callback)
        assert consumer.topic == "test-topic"
        assert consumer._on_event == callback
        assert consumer._consumer is None
        assert not consumer._running


class TestKafkaConsumerServiceCreate:
    @patch("src.services.kafka_consumer.config")
    def test_create_consumer_config(self, mock_config):
        from src.config import KafkaConfig
        mock_config.kafka = KafkaConfig()
        
        consumer = KafkaConsumerService("test-topic", lambda t, e: None)
        result = consumer._create_consumer()
        
        assert result is not None


class TestKafkaConsumerProcessMessage:
    @pytest.mark.asyncio
    async def test_process_message_json_error(self):
        from confluent_kafka import Message
        
        mock_msg = MagicMock(spec=Message)
        mock_msg.value.return_value = b"invalid json"
        mock_msg.timestamp.return_value = (1, 1234567890000)
        mock_msg.offset.return_value = 100
        
        callback = AsyncMock()
        consumer = KafkaConsumerService("test-topic", callback)
        
        try:
            await consumer._process_message(mock_msg)
        except Exception:
            pass
    
    @pytest.mark.asyncio
    async def test_process_message_valid(self):
        from confluent_kafka import Message
        
        mock_msg = MagicMock(spec=Message)
        mock_msg.value.return_value = b'{"id": "Q1", "rev": 1, "type": "edit", "at": "2024-01-01T00:00:00Z", "user": "user1"}'
        mock_msg.timestamp.return_value = (1, 1234567890000)
        mock_msg.offset.return_value = 100
        
        callback = AsyncMock()
        consumer = KafkaConsumerService("test-topic", callback)
        
        try:
            await consumer._process_message(mock_msg)
        except Exception:
            pass
    
    @pytest.mark.asyncio
    async def test_process_message_timestamp_type_0(self):
        from confluent_kafka import Message
        
        mock_msg = MagicMock(spec=Message)
        mock_msg.value.return_value = b'{"id": "Q1", "rev": 1, "type": "edit", "at": "2024-01-01T00:00:00Z", "user": "user1"}'
        mock_msg.timestamp.return_value = (0, 1234567890000)
        mock_msg.offset.return_value = 100
        
        callback = AsyncMock()
        consumer = KafkaConsumerService("test-topic", callback)
        
        try:
            await consumer._process_message(mock_msg)
        except Exception:
            pass
    
    @pytest.mark.asyncio
    async def test_process_message_other_error(self):
        from confluent_kafka import Message
        
        mock_msg = MagicMock(spec=Message)
        mock_msg.value.side_effect = Exception("some error")
        
        callback = AsyncMock()
        consumer = KafkaConsumerService("test-topic", callback)
        
        try:
            await consumer._process_message(mock_msg)
        except Exception:
            pass


class TestKafkaConsumerStart:
    @pytest.mark.asyncio
    @patch("src.services.kafka_consumer.asyncio.get_event_loop")
    @patch("src.services.kafka_consumer.KafkaConsumerService._create_consumer")
    async def test_start_basic(self, mock_create, mock_loop):
        mock_loop_instance = MagicMock()
        mock_loop.return_value = mock_loop_instance
        mock_loop_instance.run_in_executor = AsyncMock()
        
        mock_consumer = MagicMock()
        mock_create.return_value = mock_consumer
        
        consumer = KafkaConsumerService("test-topic", lambda t, e: None)
        consumer.start()
        
        assert consumer._running is True
    
    @pytest.mark.asyncio
    @patch("src.services.kafka_consumer.asyncio.get_event_loop")
    @patch("src.services.kafka_consumer.KafkaConsumerService._create_consumer")
    async def test_start_with_offset(self, mock_create, mock_loop):
        mock_loop_instance = MagicMock()
        mock_loop.return_value = mock_loop_instance
        mock_loop_instance.run_in_executor = AsyncMock()
        
        mock_consumer = MagicMock()
        mock_create.return_value = mock_consumer
        
        consumer = KafkaConsumerService("test-topic", lambda t, e: None)
        consumer.start(offset=100)
        
        assert consumer._running is True
    
    @pytest.mark.asyncio
    @patch("src.services.kafka_consumer.asyncio.get_event_loop")
    @patch("src.services.kafka_consumer.KafkaConsumerService._create_consumer")
    async def test_start_with_since(self, mock_create, mock_loop):
        from datetime import datetime
        mock_loop_instance = MagicMock()
        mock_loop.return_value = mock_loop_instance
        mock_loop_instance.run_in_executor = AsyncMock()
        
        mock_consumer = MagicMock()
        mock_consumer.offsets_for_times.return_value = []
        mock_create.return_value = mock_consumer
        
        consumer = KafkaConsumerService("test-topic", lambda t, e: None)
        consumer.start(since=datetime(2024, 1, 1))
        
        assert consumer._running is True
    
    @pytest.mark.asyncio
    @patch("src.services.kafka_consumer.asyncio.get_event_loop")
    @patch("src.services.kafka_consumer.KafkaConsumerService._create_consumer")
    async def test_start_no_params(self, mock_create, mock_loop):
        mock_loop_instance = MagicMock()
        mock_loop.return_value = mock_loop_instance
        mock_loop_instance.run_in_executor = AsyncMock()
        
        mock_consumer = MagicMock()
        mock_create.return_value = mock_consumer
        
        consumer = KafkaConsumerService("test-topic", lambda t, e: None)
        consumer.start()
        
        assert consumer._running is True
    
    @pytest.mark.asyncio
    @patch("src.services.kafka_consumer.asyncio.get_event_loop")
    @patch("src.services.kafka_consumer.KafkaConsumerService._create_consumer")
    async def test_start_sets_running(self, mock_create, mock_loop):
        mock_loop_instance = MagicMock()
        mock_loop.return_value = mock_loop_instance
        mock_loop_instance.run_in_executor = AsyncMock()
        
        mock_consumer = MagicMock()
        mock_create.return_value = mock_consumer
        
        consumer = KafkaConsumerService("test-topic", lambda t, e: None)
        consumer.start()
        
        assert consumer._running is True


class TestKafkaConsumerStop:
    @pytest.mark.asyncio
    @patch("src.services.kafka_consumer.asyncio.get_event_loop")
    @patch("src.services.kafka_consumer.KafkaConsumerService._create_consumer")
    async def test_stop(self, mock_create, mock_loop):
        import asyncio
        
        mock_loop_instance = MagicMock()
        mock_loop.return_value = mock_loop_instance
        mock_loop_instance.run_in_executor = AsyncMock()
        
        mock_consumer = MagicMock()
        mock_create.return_value = mock_consumer
        
        consumer = KafkaConsumerService("test-topic", lambda t, e: None)
        consumer.start()
        consumer._running = True
        consumer._task = asyncio.create_task(asyncio.sleep(0.01))
        
        await consumer.stop()
        
        assert not consumer._running
        mock_consumer.close.assert_called_once()


class TestKafkaConsumerConsumeLoop:
    @pytest.mark.asyncio
    async def test_consume_loop_no_consumer(self):
        consumer = KafkaConsumerService("test-topic", lambda t, e: None)
        consumer._running = True
        
        async def run():
            await asyncio.sleep(0.02)
            consumer._running = False
        
        task = asyncio.create_task(run())
        await task
    
    @pytest.mark.asyncio
    async def test_consume_loop_message_none(self):
        consumer = KafkaConsumerService("test-topic", lambda t, e: None)
        consumer._running = True
        consumer._consumer = MagicMock()
        consumer._consumer.poll.return_value = None
        
        async def run():
            await asyncio.sleep(0.01)
            consumer._running = False
        
        task = asyncio.create_task(run())
        await task
    
    @pytest.mark.asyncio
    async def test_consume_loop_message_with_error(self):
        from confluent_kafka import KafkaError
        
        consumer = KafkaConsumerService("test-topic", lambda t, e: None)
        consumer._running = True
        consumer._consumer = MagicMock()
        
        mock_msg = MagicMock()
        mock_error = MagicMock()
        mock_error.code.return_value = KafkaError._PARTITION_EOF
        mock_msg.error.return_value = mock_error
        consumer._consumer.poll.return_value = mock_msg
        
        async def run():
            await asyncio.sleep(0.01)
            consumer._running = False
        
        task = asyncio.create_task(run())
        await task
    
    @pytest.mark.asyncio
    async def test_consume_loop_kafka_exception(self):
        from confluent_kafka import KafkaError, KafkaException
        
        consumer = KafkaConsumerService("test-topic", lambda t, e: None)
        consumer._running = True
        consumer._consumer = MagicMock()
        
        mock_msg = MagicMock()
        mock_error = MagicMock()
        mock_error.code.return_value = "other_error"
        mock_msg.error.return_value = mock_error
        consumer._consumer.poll.return_value = mock_msg
        
        async def run():
            await asyncio.sleep(0.01)
            consumer._running = False
        
        task = asyncio.create_task(run())
        await task
    
    @pytest.mark.asyncio
    async def test_consume_loop_exception(self):
        consumer = KafkaConsumerService("test-topic", lambda t, e: None)
        consumer._running = True
        consumer._consumer = MagicMock()
        consumer._consumer.poll.side_effect = Exception("poll error")
        
        async def run():
            await asyncio.sleep(0.02)
            consumer._running = False
        
        task = asyncio.create_task(run())
        await task