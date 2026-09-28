import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Optional

from src.config import config
from src.models.sse_event import SSEEvent
from src.services.client_connection import ClientConnection
from src.services.event_router import EventRouter
from src.services.kafka_consumer import KafkaConsumerService
from src.services.redis_state import redis_state

logger = logging.getLogger(__name__)


class StreamManager:
    """Manages Kafka consumers and SSE client connections, handles subscription/unsubscription."""
    
    def __init__(self):
        self._topics: dict[str, KafkaConsumerService] = {}
        self._clients: dict[str, set[ClientConnection]] = defaultdict(set)
        self._router = EventRouter(self._route_event)
        self._lock = asyncio.Lock()
        self._worker_id = str(uuid.uuid4())[:8]

    def _route_event(self, topic: str, event: SSEEvent):
        logger.info(f"_route_event called for topic {topic}, event {event.id}")
        for client in list(self._clients.get(topic, [])):
            if client.disconnected:
                continue
            try:
                client.queue.put_nowait(event)
                logger.info(f"Event {event.id} added to client {client.id} queue, queue size now ~{client.queue.qsize()}")
            except asyncio.QueueFull:
                try:
                    client.queue.get_nowait()
                    client.queue.put_nowait(event)
                    logger.warning(
                        f"Client {client.id} for topic {topic} slow, dropped oldest event"
                    )
                except asyncio.QueueEmpty:
                    pass

    async def subscribe(
        self,
        topic: str,
        offset: Optional[int] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> ClientConnection:
        logger.info(f"subscribe called for topic={topic}, offset={offset}")
        
        # Try to acquire lock with timeout
        try:
            async with asyncio.timeout(5):
                async with self._lock:
                    logger.info(f"Lock acquired for topic={topic}")
                    if topic not in self._topics:
                        logger.info(f"Creating new consumer for topic={topic}")
                        consumer = KafkaConsumerService(topic, self._router.route)
                        consumer.start(offset=offset, since=since)
                        self._topics[topic] = consumer
                        await redis_state.register_consumer(topic, self._worker_id)
                        logger.info(f"Created new Kafka consumer for topic {topic}")

                    client = ClientConnection(queue_size=config.kafka.client_queue_size)
                    client.limit = limit
                    self._clients[topic].add(client)
                    await redis_state.increment_client_count(topic)
                    logger.info(
                        f"Client {client.id} subscribed to topic {topic} "
                        f"(offset={offset}, since={since}, limit={limit})"
                    )
                    return client
        except asyncio.TimeoutError:
            logger.error(f"Timeout acquiring lock for topic {topic}")
            raise

    async def unsubscribe(self, topic: str, client: ClientConnection):
        async with self._lock:
            client.disconnected = True
            if topic in self._clients:
                self._clients[topic].discard(client)
                await redis_state.decrement_client_count(topic)
                if not self._clients[topic]:
                    consumer = self._topics.pop(topic, None)
                    if consumer:
                        await consumer.stop()
                    await redis_state.unregister_consumer(topic, self._worker_id)
                    logger.info(f"Stopped Kafka consumer for topic {topic}")

    def get_topics(self) -> list[str]:
        return list(self._topics.keys())

    async def get_topic_metadata(self, topic: str) -> dict | None:
        worker_count = await redis_state.get_worker_count(topic)
        has_local_consumer = topic in self._topics

        if worker_count == 0 and not has_local_consumer:
            return None

        low, high = await asyncio.to_thread(self._get_watermark_offsets, topic)
        client_count = await redis_state.get_client_count(topic)
        return {
            "topic": topic,
            "earliest_offset": low,
            "latest_offset": high,
            "message_count": high - low if high > 0 and low >= 0 else 0,
            "connected_clients": client_count,
        }

    def _get_watermark_offsets(self, topic: str) -> tuple[int, int]:
        from confluent_kafka import Consumer, TopicPartition

        try:
            consumer = Consumer({
                "bootstrap.servers": config.kafka.brokers,
                "group.id": "metadata-reader",
            })
            metadata = consumer.list_topics(topic, timeout=5)
            topic_meta = metadata.topics.get(topic)
            if not topic_meta:
                logger.warning(f"Topic {topic} not found in metadata")
                consumer.close()
                return (0, 0)

            partitions = topic_meta.partitions
            logger.info(f"Topic {topic} has {len(partitions)} partitions")
            if partitions:
                partition_id = list(partitions.keys())[0]
                tp = TopicPartition(topic, partition_id)
                low, high = consumer.get_watermark_offsets(tp)
                logger.info(f"Watermarks for {topic}: partition={partition_id}, low={low}, high={high}")
                consumer.close()
                return (low, high)
            consumer.close()
            return (0, 0)
        except Exception:
            logger.exception(f"Error getting watermark offsets for {topic}")
            return (0, 0)

    async def shutdown(self):
        async with self._lock:
            for topic, consumer in self._topics.items():
                await consumer.stop()
                await redis_state.unregister_consumer(topic, self._worker_id)
            self._topics.clear()
            self._clients.clear()


stream_manager = StreamManager()
