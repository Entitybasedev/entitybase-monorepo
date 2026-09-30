# Port Reference

This document lists all exposed ports in the Entitybase docker stack.

## Format

Host Port → Container Port (Service Name)

## Infrastructure

| Host Port | Container Port | Service | Description |
|-----------|----------------|---------|-------------|
| 3306 | 3306 | mysql | MySQL database |
| 9092 | 9092 | redpanda | Redpanda broker |

## Core Services

| Host Port | Container Port | Service | Description |
|-----------|----------------|---------|-------------|
| 8080 | 8080 | entitybase-frontend | UI (entities + change stream) |
| 8083 | 8080 | entitybase-api | REST API |
| 8888 | 8888 | kafka2sse-backend | Change events as SSE |

Internal-only ports: valkey 6379, redpanda admin 9644 (not exposed to the host).
