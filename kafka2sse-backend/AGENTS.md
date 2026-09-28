# AGENTS.md - kafka2sse-backend

## Project Overview

A Kafka to SSE (Server-Sent Events) gateway that streams Kafka messages to clients via HTTP.

## Code Conventions

### One Class Per File

Each class must be in its own file:
- `src/services/stream_manager.py` - StreamManager class only
- `src/services/redis_state.py` - RedisState class only
- `src/services/client_connection.py` - ClientConnection class only
- `src/services/kafka_consumer.py` - KafkaConsumerService class only
- `src/services/sse_broadcaster.py` - SSEBroadcaster class only
- `src/services/event_router.py` - EventRouter class only

## Architecture

- **StreamManager**: Manages Kafka consumers and SSE client connections
- **RedisState**: Shares state between multiple uvicorn workers via Valkey
- **ClientConnection**: Represents an SSE client connection
- **KafkaConsumerService**: Wraps Kafka consumer for a single topic
- **SSEBroadcaster**: Formats and streams events to SSE clients
- **EventRouter**: Routes Kafka messages to registered clients

## Dependencies

- FastAPI for HTTP server
- confluent-kafka for Kafka consumer
- valkey (Redis alternative) for shared state between workers
- sse-starlette for SSE support

## Testing Requirements

- Minimum 80% code coverage required
- Tests must be placed in `tests/go/` directory at project root
- Use pytest with pytest-asyncio for async tests
- Use pytest-cov for coverage reporting

## Environment Variables

- `KAFKA_BROKERS`: Kafka broker addresses (default: localhost:9092)
- `VALKEY_HOST`: Valkey host (default: localhost)
- `VALKEY_PORT`: Valkey port (default: 6379)
- `KAFKA_CLIENT_QUEUE_SIZE`: Max queue size per client (default: 100)
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8888)
