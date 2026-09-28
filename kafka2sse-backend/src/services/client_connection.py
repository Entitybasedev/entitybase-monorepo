import asyncio
import uuid

from src.models.sse_event import SSEEvent


class ClientConnection:
    """Represents an SSE client connection with event queue."""
    
    def __init__(self, queue_size: int = 100):
        self.id = str(uuid.uuid4())[:8]
        self.queue: asyncio.Queue[SSEEvent] = asyncio.Queue(maxsize=queue_size)
        self.events_sent = 0
        self.limit: int | None = None
        self.disconnected = False
