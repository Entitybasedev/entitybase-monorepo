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


class Config(BaseModel):
    """Main configuration container for the application."""
    kafka: KafkaConfig = KafkaConfig()
    valkey: ValkeyConfig = ValkeyConfig()
    server: ServerConfig = ServerConfig()

    @cached_property
    def kafka_broker_list(self) -> list[str]:
        return [b.strip() for b in self.kafka.brokers.split(",") if b.strip()]


config = Config()
