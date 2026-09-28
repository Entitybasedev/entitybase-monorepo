# CHANGELOG

## [1.0.0] - 2026-03-09

### Added
- Valkey (Redis alternative) for shared state between workers
- `/v1/streams/{topic}/metadata` endpoint to query message count
- SSE stream now properly delivers Kafka events to clients

### Fixed
- Kafka consumer was blocking the async event loop - now runs in thread pool
- SSE stream now delivers events in real-time when items are created

### Changes
- Uses single worker mode (uvicorn without --workers) due to Kafka consumer threading model
- Metadata endpoint queries Kafka directly instead of using in-memory state
