import pytest
from unittest.mock import MagicMock, patch

from src.services.redis_state import RedisState


@patch("src.services.redis_state.valkey.Valkey")
class TestRedisState:
    def test_init(self, mock_valkey):
        rs = RedisState()
        assert rs._client is None

    @pytest.mark.asyncio
    async def test_register_consumer(self, mock_valkey):
        rs = RedisState()
        mock_client = MagicMock()
        rs._client = mock_client
        
        await rs.register_consumer("test-topic", "worker1")
        
        mock_client.sadd.assert_called_once()
        mock_client.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_unregister_consumer(self, mock_valkey):
        rs = RedisState()
        mock_client = MagicMock()
        rs._client = mock_client
        
        await rs.unregister_consumer("test-topic", "worker1")
        
        mock_client.srem.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_topics(self, mock_valkey):
        rs = RedisState()
        mock_client = MagicMock()
        mock_client.keys.return_value = ["kafka2sse:topics:topic1:workers", "kafka2sse:topics:topic2:workers"]
        mock_client.scard.side_effect = lambda k: 1
        rs._client = mock_client
        
        topics = await rs.get_active_topics()
        
        assert "topic1" in topics

    @pytest.mark.asyncio
    async def test_get_worker_count(self, mock_valkey):
        rs = RedisState()
        mock_client = MagicMock()
        mock_client.scard.return_value = 3
        rs._client = mock_client
        
        count = await rs.get_worker_count("test-topic")
        
        assert count == 3

    @pytest.mark.asyncio
    async def test_increment_client_count(self, mock_valkey):
        rs = RedisState()
        mock_client = MagicMock()
        rs._client = mock_client
        
        await rs.increment_client_count("test-topic")
        
        mock_client.incr.assert_called_once()
        mock_client.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_decrement_client_count(self, mock_valkey):
        rs = RedisState()
        mock_client = MagicMock()
        rs._client = mock_client
        
        await rs.decrement_client_count("test-topic")
        
        mock_client.decr.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_client_count_with_value(self, mock_valkey):
        rs = RedisState()
        mock_client = MagicMock()
        mock_client.get.return_value = "5"
        rs._client = mock_client
        
        count = await rs.get_client_count("test-topic")
        
        assert count == 5

    @pytest.mark.asyncio
    async def test_get_client_count_empty(self, mock_valkey):
        rs = RedisState()
        mock_client = MagicMock()
        mock_client.get.return_value = None
        rs._client = mock_client
        
        count = await rs.get_client_count("test-topic")
        
        assert count == 0