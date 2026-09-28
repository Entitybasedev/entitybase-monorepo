import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Callable, Optional

from confluent_kafka import Consumer, KafkaError, KafkaException, TopicPartition

from src.config import config
from src.models.entity_change import EntityChange
from src.models.sse_event import SSEEvent

logger = logging.getLogger(__name__)


class KafkaConsumerService:
    """Wraps a Kafka consumer for a single topic, processes messages and routes to callback."""
    
    def __init__(self, topic: str, on_event: Callable[[str, SSEEvent], None]):
        self.topic = topic
        self._on_event = on_event
        self._consumer: Optional[Consumer] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def _create_consumer(self) -> Consumer:
        conf = {
            "bootstrap.servers": config.kafka.brokers,
            "group.id": f"kafka2sse-{self.topic}",
            "auto.offset.reset": "latest",
            "enable.auto.commit": True,
        }
        return Consumer(conf)

    async def _consume_loop(self):
        import os
        worker_pid = os.getpid()
        logger.info(f"Starting consume loop for {self.topic} in worker {worker_pid}")
        while self._running:
            try:
                msg = self._consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    logger.error(f"Kafka error: {msg.error()}")
                    raise KafkaException(msg.error())

                logger.info(f"[Worker {worker_pid}] Received message from Kafka: offset={msg.offset()}")
                await self._process_message(msg)
            except Exception as e:
                logger.exception(f"Error in consume loop: {e}")
                await asyncio.sleep(1)

    async def _process_message(self, msg: Any):
        try:
            value = json.loads(msg.value().decode("utf-8"))
            entity_change = EntityChange(**value)

            event_id = str(msg.offset())
            if msg.timestamp()[0] == 1:
                event_id = str(msg.timestamp()[1])

            sse_event = SSEEvent(
                event_type="entity_change",
                id=event_id,
                data=entity_change,
            )
            self._on_event(self.topic, sse_event)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to decode message: {e}")
        except Exception as e:
            logger.exception(f"Failed to process message: {e}")

    def start(
        self,
        offset: Optional[int] = None,
        since: Optional[datetime] = None,
    ):
        logger.info(f"Starting Kafka consumer for {self.topic}")
        self._consumer = self._create_consumer()
        self._running = True

        # Run blocking Kafka operations in thread pool
        def setup_consumer():
            if offset is not None:
                self._consumer.assign([TopicPartition(self.topic, 0, offset)])
                logger.info(f"Consumer for {self.topic} seeked to offset {offset}")
            elif since is not None:
                timestamp_ms = int(since.timestamp() * 1000)
                offsets = self._consumer.offsets_for_times(
                    [TopicPartition(self.topic, 0, timestamp_ms)]
                )
                if offsets:
                    self._consumer.assign(offsets)
                    logger.info(f"Consumer for {self.topic} seeked to timestamp {since}")
                else:
                    self._consumer.subscribe([self.topic])
                    logger.warning(
                        f"No offset found for timestamp {since}, subscribing from latest"
                    )
            else:
                self._consumer.subscribe([self.topic])
                logger.info(f"Consumer for {self.topic} subscribed from latest")

        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, setup_consumer)

        self._task = asyncio.create_task(self._consume_loop())
        logger.info(f"Kafka consumer for topic {self.topic} started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._consumer:
            self._consumer.close()
        logger.info(f"Kafka consumer for topic {self.topic} stopped")
