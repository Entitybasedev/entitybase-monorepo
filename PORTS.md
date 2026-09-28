# Port Reference

This document lists all exposed ports in the Entitybase orchestrator.

## Format

Host Port → Container Port (Service Name)

## Infrastructure

| Host Port | Container Port | Service | Description |
|-----------|----------------|---------|-------------|
| 3307 | 8080 | mysql-health | MySQL health proxy |
| 9000 | 9000 | minio | S3 API |
| 9001 | 9001 | minio | S3 Console |
| 6378 | 8080 | valkey-health | Valkey health proxy |
| 9092 | 9092 | redpanda | Kafka broker |
| 8084 | 8080 | redpanda-console | Kafka UI |
| 9645 | 9644 | redpanda-health | Redpanda admin |

## Core Services

| Host Port | Container Port | Service | Description |
|-----------|----------------|---------|-------------|
| 8083 | 8080 | entitybase-api | REST API |
| 8001 | 8001 | idworker | ID generation service |
| 8888 | 8888 | kafka2sse-backend | SSE API |
| 8889 | 8889 | kafka2sse-frontend | SSE UI |
| 8080 | 8083 | entitybase-orchestrator-frontend | Orchestrator UI |

## Workers

| Host Port | Container Port | Service | Description |
|-----------|----------------|---------|-------------|
| 8002 | 8002 | json-dump-worker | JSON export worker |
| 8003 | 8003 | ttl-dump-worker | TTL/expire worker |
| 8004 | 8004 | backlink-stats-worker | Backlink statistics |
| 8005 | 8005 | general-stats-worker | General statistics |
| 8006 | 8006 | user-stats-worker | User statistics |
| 8007 | 8007 | elasticsearch-indexer-worker | Elasticsearch indexing |
| 8008 | 8008 | purge-worker | Data purge worker |
| 8009 | 8009 | meilisearch-indexer-worker | Meilisearch indexing |

## Search

| Host Port | Container Port | Service | Description |
|-----------|----------------|---------|-------------|
| 9200 | 9200 | elasticsearch | Search engine |
| 9201 | 8080 | elasticsearch-health | ES health proxy |
| 7700 | 7700 | meilisearch | Full-text search |
| 7701 | 8080 | meilisearch-health | Meilisearch health proxy |