"""
Kafka-to-SSE streaming service.

Architecture:
- SSE endpoint creates a thread-local Kafka consumer that runs in a thread pool
  (via asyncio event loop's run_in_executor) to avoid blocking the async event loop.
- The Kafka consumer polls messages and puts them into an asyncio.Queue shared with
  the async event_generator.
- This design allows the FastAPI server to remain responsive while streaming SSE.

Thread pool explanation:
- asyncio.run_in_executor(None, func) runs func in Python's default ThreadPoolExecutor
- confluent-kafka Consumer.poll() is a blocking call - it waits until a message arrives
- Without the thread pool, poll() would block the entire event loop, freezing all requests

Example:
    >>> loop = asyncio.get_event_loop()
    >>> kafka_task = loop.run_in_executor(None, blocking_kafka_function)
    This runs blocking_kafka_function in a separate thread, keeping the event loop responsive.
"""

import logging
import logging.config
import os

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "default": {
            "level": LOG_LEVEL,
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {"level": LOG_LEVEL, "handlers": ["default"], "propagate": False},
        "uvicorn.error": {"level": "DEBUG", "handlers": ["default"]},
        "uvicorn.access": {"level": "DEBUG", "handlers": ["default"]},
        "rdkafka": {"level": "INFO", "handlers": ["default"]},
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
import asyncio
import json
import logging
import sys
from contextlib import asynccontextmanager
from typing import Any

from confluent_kafka import KafkaError, KafkaException, Producer
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sse_starlette import EventSourceResponse


def get_available_topics() -> list[str]:
    try:
        producer = Producer({"bootstrap.servers": config.kafka.brokers})
        cluster_metadata = producer.list_topics(timeout=5)
        return sorted(
            topic
            for topic in cluster_metadata.topics.keys()
            if not topic.startswith("_")
        )
    except KafkaException as e:
        if e.args[0].code() == KafkaError._TRANSPORT:
            return []
        raise


from src.config import config  # noqa: E402
from src.models.entity_change import EntityChange  # noqa: E402
from src.models.sse_event import SSEEvent  # noqa: E402
from src.services.client_connection import ClientConnection  # noqa: E402
from src.services.stream_manager import stream_manager  # noqa: E402


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Configure librdkafka to use Python's logging with timestamps
for logger_name in ["rdkafka", "rdkafka.int", "rdkafka.conn", "rdkafka consumer"]:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)

# Suppress confluent_kafka debug logs
logging.getLogger("confluent_kafka").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await stream_manager.shutdown()


app = FastAPI(
    title="Kafka2SSE API",
    version=config.server.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    kafka: str
    backend_type: str = "unknown"


def _detect_backend_type(metadata: Any) -> str:
    """Detect if the backend is Kafka or Redpanda from broker metadata."""
    if not metadata or not metadata.brokers:
        return "unknown"
    
    # Check cluster ID - Redpanda typically has "redpanda" in the cluster ID
    if metadata.cluster_id and "redpanda" in metadata.cluster_id.lower():
        return "redpanda"
    
    # Check broker version - Redpanda reports as version 0.0.0 but has specific features
    # Default to kafka as it's the most common
    return "kafka"


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    kafka_status = "disconnected"
    backend_type = "unknown"
    try:
        producer = Producer({
            "bootstrap.servers": config.kafka.brokers,
            "socket.timeout.ms": 3000,
            "metadata.request.timeout.ms": 5000,
        })
        metadata = producer.list_topics(timeout=3)
        kafka_status = "connected"
        backend_type = _detect_backend_type(metadata)
    except KafkaException:
        pass

    return HealthResponse(
        status="ok" if kafka_status == "connected" else "degraded",
        kafka=kafka_status,
        backend_type=backend_type,
    )


@app.get("/v1/topics")
async def list_topics():
    return {"topics": get_available_topics()}


@app.get("/v1/streams/{topic}/metadata")
async def stream_metadata(topic: str):
    from confluent_kafka import Consumer, TopicPartition

    try:
        consumer = Consumer({
            "bootstrap.servers": config.kafka.brokers,
            "group.id": "metadata-reader",
        })
        metadata = consumer.list_topics(topic, timeout=5)
        topic_meta = metadata.topics.get(topic)
        if not topic_meta:
            consumer.close()
            return {
                "topic": topic,
                "earliest_offset": 0,
                "latest_offset": 0,
                "message_count": 0,
            }

        partitions = topic_meta.partitions
        if partitions:
            partition_id = list(partitions.keys())[0]
            tp = TopicPartition(topic, partition_id)
            low, high = consumer.get_watermark_offsets(tp)
            consumer.close()
            return {
                "topic": topic,
                "earliest_offset": low,
                "latest_offset": high,
                "message_count": high - low if high > 0 and low >= 0 else 0,
            }
        consumer.close()
        return {
            "topic": topic,
            "earliest_offset": 0,
            "latest_offset": 0,
            "message_count": 0,
        }
    except Exception as e:
        logger.exception(f"Error getting metadata for {topic}")
        return {
            "topic": topic,
            "earliest_offset": 0,
            "latest_offset": 0,
            "message_count": 0,
            "error": str(e),
        }


@app.get("/v1/streams/{topic}")
async def stream(
    topic: str,
    offset: int | None = None,
    since: str | None = None,
    limit: int | None = None,
):
    logger.info(f"=== STREAM ENDPOINT CALLED ===")
    logger.info(f"topic={topic}, offset={offset}, offset_type={type(offset)}, since={since}, limit={limit}")
    
    """
    Stream SSE events from a Kafka topic.
    
    Implementation uses thread pool executor for Kafka consumer:
    - Creates a blocking kafka_consumer_thread() that calls Consumer.poll()
    - Runs it in thread pool via loop.run_in_executor()
    - Shares events via asyncio.Queue with the async event_generator()
    
    This prevents poll() from blocking the FastAPI event loop.
    
    Args:
        topic: Kafka topic to stream from
        offset: Starting offset (optional)
        since: Start from timestamp (optional)
        limit: Maximum events to send before closing (optional)
    
    Returns:
        Server-Sent Events response that streams Kafka messages as JSON.
    """
    logger.info(f"Stream endpoint called for topic={topic}, offset={offset}, limit={limit}")

    # Create a client connection
    client = ClientConnection(queue_size=100)
    client.limit = limit
    logger.info(f"Created client with limit={client.limit}")

    log_prefix = f"kafka2sse-{topic}-{client.id}"

    class RebalanceListener:
        """Listener for Kafka rebalance events - logs for debugging."""
        
        def __init__(self, log_prefix: str):
            self.log_prefix = log_prefix
        
        async def on_partitions_assigned(self, consumer, partitions):
            logger.info(f"[{self.log_prefix}] Partitions ASSIGNED: {partitions}")
        
        async def on_partitions_revoked(self, consumer, partitions):
            logger.info(f"[{self.log_prefix}] Partitions REVOKED: {partitions}")
        
        async def on_partitions_lost(self, consumer, partitions):
            logger.warning(f"[{self.log_prefix}] Partitions LOST: {partitions}")

    async def kafka_consumer():
        """
        Async Kafka consumer using aiokafka.
        
        aiokafka provides reliable offset seeking with assign() + seek().
        Runs directly in async context - no thread pool needed.
        """
        from aiokafka import AIOKafkaConsumer
        from aiokafka.structs import TopicPartition
        
        log_prefix = f"kafka2sse-{topic}-{client.id}"
        consumer = None
        
        try:
            consumer = AIOKafkaConsumer(
                bootstrap_servers=config.kafka.brokers,
                group_id=log_prefix,
                enable_auto_commit=False,
                auto_offset_reset="earliest",
                request_timeout_ms=30000,
                retry_backoff_ms=1000,
            )
            
            logger.info(f"[{log_prefix}] Starting Kafka consumer for {topic}")
            
            await consumer.start()
            logger.info(f"[{log_prefix}] Consumer started")
            
            if offset is not None:
                # Use assign() for precise offset seeking  
                try:
                    tp = TopicPartition(topic, 0)
                    await consumer.assign([tp])
                    await consumer.seek(tp, offset)
                    logger.info(f"[{log_prefix}] Assigned partition {tp} and seeked to offset {offset}")
                except Exception as e:
                    logger.warning(f"[{log_prefix}] Failed to seek to offset {offset}: {e}, falling back to subscribe")
                    consumer.subscribe([topic])
            else:
                # Subscribe directly - triggers metadata fetch
                consumer.subscribe([topic])
            
            logger.info(f"[{log_prefix}] Subscribed to topic {topic}")

            logger.info(f"[{log_prefix}] Starting consumption loop...")
            
            # Track assignment changes
            last_assignment = set()
            
            # Use getmany() for more explicit control instead of async for
            while True:
                # Check if limit reached
                if client.limit and client.events_sent >= client.limit:
                    logger.info(f"[{log_prefix}] Limit reached: {client.events_sent}/{client.limit}")
                    break
                
                # Check current assignment
                current_assignment = consumer.assignment()
                if current_assignment != last_assignment:
                    logger.info(f"[{log_prefix}] Assignment changed: {current_assignment}")
                    last_assignment = current_assignment
                
                # Use getmany for explicit control
                logger.debug(f"[{log_prefix}] Waiting for messages...")
                records = await consumer.getmany(timeout_ms=1000)
                
                if not records:
                    logger.debug(f"[{log_prefix}] No messages in this poll")
                    # Continue waiting
                    continue
                
                logger.info(f"[{log_prefix}] Received {sum(len(msgs) for msgs in records.values())} messages")
                
                for tp, messages in records.items():
                    for msg in messages:
                        logger.debug(f"Kafka message: topic={msg.topic}, partition={msg.partition}, offset={msg.offset}, key={msg.key}")

                        raw_value = None
                        try:
                            raw_value = msg.value.decode("utf-8")
                            logger.debug(f"Kafka raw value: {raw_value}")
                            value = json.loads(raw_value)
                            entity_change = EntityChange(**value)
                            logger.info(f"[{log_prefix}] Parsed entity_change: entity_id={entity_change.entity_id}, change_type={entity_change.change_type}, revision_id={entity_change.revision_id}")
                            event = SSEEvent(
                                event_type="entity_change",
                                id=str(msg.offset),
                                data=entity_change,
                            )
                            client.events_sent += 1
                            try:
                                client.queue.put_nowait(event)
                                logger.debug(f"Event queued to client: offset={msg.offset}, queue_size={client.queue.qsize()}")
                            except asyncio.QueueFull:
                                try:
                                    client.queue.get_nowait()
                                    client.queue.put_nowait(event)
                                    logger.debug(f"Event queued (replaced): offset={msg.offset}")
                                except Exception as e:
                                    logger.warning(f"Queue full and replace failed: {e}")
                        except Exception as e:
                            logger.warning(f"Failed to process message: {e}, offset={msg.offset}, raw_value={raw_value or 'N/A'}")
        except asyncio.CancelledError:
            logger.info(f"[{log_prefix}] Consumer task cancelled")
        except Exception as e:
            logger.exception(f"[{log_prefix}] ERROR in kafka_consumer: {e}")
        finally:
            if 'consumer' in locals():
                try:
                    await consumer.stop()
                except Exception as e:
                    logger.warning(f"[{log_prefix}] Error stopping consumer: {e}")
            logger.info(f"[{log_prefix}] Kafka consumer cleanup done")

    kafka_task = asyncio.create_task(kafka_consumer())

    async def event_generator():
        logger.info(f"[{log_prefix}] event_generator started, client.limit={client.limit}")
        try:
            while True:
                if client.limit and client.events_sent >= client.limit:
                    logger.info(f"[{log_prefix}] Limit reached: {client.events_sent}/{client.limit}")
                    break
                try:
                    event = await asyncio.wait_for(client.queue.get(), timeout=30)
                    logger.debug(f"[{log_prefix}] Sending SSE event: id={event.id}, entity_id={event.data.entity_id}")
                    data = event.model_dump_json()
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    yield "data: {\"ping\": true}\n\n"
        except asyncio.CancelledError:
            logger.info("Event generator cancelled")
        finally:
            kafka_task.cancel()

    return EventSourceResponse(event_generator())


@app.get("/")
async def root():
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
        log_config=LOGGING_CONFIG,
    )
