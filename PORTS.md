# Port Reference

This document lists all exposed ports in the Entitybase stack.

## Format

Host Port → Container Port (Service Name)

## Infrastructure

| Host Port | Container Port | Service | Description |
|-----------|----------------|---------|-------------|
| 3307 | 8080 | mysql-health | MySQL health proxy |
| 9000 | 9000 | rustfs | S3 API |
| 9001 | 9001 | rustfs | S3 Console |
| 6378 | 8080 | valkey-health | Valkey health proxy |
| 9092 | 9092 | redpanda | Kafka broker |
| 8084 | 8080 | redpanda-console | Kafka UI |
| 9645 | 9644 | redpanda-health | Redpanda admin |

## Core Services

| Host Port | Container Port | Service | Description |
|-----------|----------------|---------|-------------|
| 8083 | 8080 | entitybase-api | REST API |
| 8888 | 8888 | kafka2sse-backend | SSE API |
| 8889 | 8889 | kafka2sse-frontend | SSE UI |

## Search

| Host Port | Container Port | Service | Description |
|-----------|----------------|---------|-------------|
| 7700 | 7700 | meilisearch | Entity search index |
| 8009 | 8009 | meilisearch-indexer-worker | Keeps the index in step with the database |

## Mock servers (development only)

The mock servers used by `just e2e-mock` deliberately use the 90xx range so
they never collide with the docker stack, which owns the 80xx range.

| Host Port | Service | Description |
|-----------|---------|-------------|
| 9083 | mock-api | Mock REST API (`scripts/dev/mock-api.mjs`) |
| 9088 | mock-stream-api | Mock SSE backend (`scripts/dev/mock-stream-api.mjs`) |