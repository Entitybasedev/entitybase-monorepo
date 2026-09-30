# Quick Start

Get up and running with Entitybase Backend in 5 minutes.

## Prerequisites

- Python 3.13+
- Docker and Docker Compose
- uv (for local development)

## Option 1: Docker (Recommended)

```bash
# Start the full stack (MySQL, API, workers)
make api

# API runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

## Option 2: Local Development

```bash
# Install dependencies
uv sync --group dev

# Run tests to verify setup
make test-unit
```

## Verify It's Working

```bash
# Health check
curl http://localhost:8000/health

# Create your first item
curl -X GET http://localhost:8000/v1/entitybase/entities/items \
  -H "X-User-ID: 1" \
  -H "X-Edit-Summary: Creating my first item"

# Response: {"success":true,"data":{"entity_id":"Q1","revision_id":1}}

# Add a label
curl -X PUT http://localhost:8000/v1/entitybase/entities/Q1/labels/en \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 1" \
  -H "X-Edit-Summary: Adding label" \
  -d '{"language": "en", "value": "Hello World"}'
```

## Next Steps

- [Setup Guide](services.md) - Full environment configuration
- [Project Structure](development.md) - Understanding the codebase
- [API Endpoints](ENDPOINTS.md) - Explore the REST API
