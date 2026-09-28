import asyncio
import logging
import os

from src.models.sse_event import SSEEvent
from src.services.stream_manager import ClientConnection

logger = logging.getLogger(__name__)


class SSEBroadcaster:
    """Formats and streams SSE events to connected clients."""
    
    async def stream_events(
        self,
        client: ClientConnection,
        topic: str,
        unsubscribe_callback,
    ):
        worker_pid = os.getpid()
        logger.info(f"SSE stream started for client {client.id}, topic {topic}, worker {worker_pid}")
        try:
            while not client.disconnected:
                if client.limit and client.events_sent >= client.limit:
                    logger.info(f"Client {client.id} reached limit, closing connection")
                    break

                try:
                    event = await asyncio.wait_for(
                        client.queue.get(), timeout=30.0
                    )
                    logger.info(f"[Worker {worker_pid}] SSE got event {event.id} for client {client.id}")
                except asyncio.TimeoutError:
                    continue

                yield self._format_sse_event(event)
                client.events_sent += 1

        except asyncio.CancelledError:
            logger.info(f"Client {client.id} disconnected")
        finally:
            await unsubscribe_callback(topic, client)

    def _format_sse_event(self, event: SSEEvent) -> str:
        data = event.model_dump_json()
        return f"event: message\nid: {event.id}\ndata: {data}\n\n"
