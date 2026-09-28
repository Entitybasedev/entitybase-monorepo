import logging
from typing import Callable

from src.models.sse_event import SSEEvent

logger = logging.getLogger(__name__)


class EventRouter:
    """Routes Kafka messages to registered callbacks."""
    
    def __init__(self, on_event: Callable[[str, SSEEvent], None]):
        self._on_event = on_event

    def route(self, topic: str, event: SSEEvent):
        try:
            logger.info(f"EventRouter routing event {event.id} for topic {topic}")
            self._on_event(topic, event)
        except Exception as e:
            logger.exception(f"Error routing event for topic {topic}: {e}")
