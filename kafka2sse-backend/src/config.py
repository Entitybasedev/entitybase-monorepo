from functools import cached_property
from os import getenv

from pydantic import BaseModel


class KafkaConfig(BaseModel):
    """Configuration for Kafka broker connections."""
    brokers: str = getenv("KAFKA_BROKERS", "localhost:9092")
    client_queue_size: int = int(getenv("KAFKA_CLIENT_QUEUE_SIZE", "100"))


class ValkeyConfig(BaseModel):
    """Configuration for Valkey (Redis alternative) connections."""
    host: str = getenv("VALKEY_HOST", "localhost")
    port: int = int(getenv("VALKEY_PORT", "6379"))


class ServerConfig(BaseModel):
    """Configuration for the HTTP server."""
    host: str = getenv("HOST", "0.0.0.0")
    port: int = int(getenv("PORT", "8888"))
    app_version: str = getenv("VERSION", "v0.0.0")


class SSEConfig(BaseModel):
    """Configuration for the Server-Sent Events gateway."""

    # How long a stream stays open with nothing to send before it is closed.
    # Closing is deliberate: a consumer that never sees the stream end has no
    # point at which it can safely act on what it has read, so a follower that
    # applies changes in batches holds them until the next change arrives -
    # which, on a stream edited occasionally, means holding them indefinitely.
    # A client reconnects with Last-Event-ID and carries on where it left off.
    idle_timeout_seconds: float = float(getenv("SSE_IDLE_TIMEOUT_SECONDS", "30"))


class Config(BaseModel):
    """Main configuration container for the application."""
    kafka: KafkaConfig = KafkaConfig()
    valkey: ValkeyConfig = ValkeyConfig()
    server: ServerConfig = ServerConfig()
    sse: SSEConfig = SSEConfig()

    @cached_property
    def kafka_broker_list(self) -> list[str]:
        return [b.strip() for b in self.kafka.brokers.split(",") if b.strip()]


config = Config()
