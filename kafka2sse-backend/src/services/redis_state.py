import asyncio
import logging
from typing import Optional

import valkey

from src.config import config

logger = logging.getLogger(__name__)


class RedisState:
    """Shared state manager using Valkey (Redis alternative) for multi-worker coordination."""
    
    def __init__(self):
        self._client: Optional[valkey.Valkey] = None
        self._lock = asyncio.Lock()

    def _get_client(self) -> valkey.Valkey:
        if self._client is None:
            self._client = valkey.Valkey(
                host=config.valkey.host,
                port=config.valkey.port,
                decode_responses=True,
            )
        return self._client

    async def register_consumer(self, topic: str, worker_id: str):
        async with self._lock:
            client = self._get_client()
            key = f"kafka2sse:topics:{topic}:workers"
            client.sadd(key, worker_id)
            client.expire(key, 300)

    async def unregister_consumer(self, topic: str, worker_id: str):
        async with self._lock:
            client = self._get_client()
            key = f"kafka2sse:topics:{topic}:workers"
            client.srem(key, worker_id)

    async def get_active_topics(self) -> list[str]:
        async with self._lock:
            client = self._get_client()
            keys = client.keys("kafka2sse:topics:*:workers")
            topics = [k.split(":")[2] for k in keys if client.scard(k) > 0]
            return topics

    async def get_worker_count(self, topic: str) -> int:
        async with self._lock:
            client = self._get_client()
            key = f"kafka2sse:topics:{topic}:workers"
            return client.scard(key)

    async def increment_client_count(self, topic: str):
        async with self._lock:
            client = self._get_client()
            key = f"kafka2sse:topics:{topic}:clients"
            client.incr(key)
            client.expire(key, 300)

    async def decrement_client_count(self, topic: str):
        async with self._lock:
            client = self._get_client()
            key = f"kafka2sse:topics:{topic}:clients"
            client.decr(key)

    async def get_client_count(self, topic: str) -> int:
        async with self._lock:
            client = self._get_client()
            key = f"kafka2sse:topics:{topic}:clients"
            count = client.get(key)
            return int(count) if count else 0


redis_state = RedisState()
