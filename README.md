# Entitybase Orchestrator

Docker orchestration for Entitybase services.

## Architecture

```mermaid
flowchart TB
    subgraph Infrastructure
        MySQL[(MySQL<br/>3306)]
        Minio[MinIO<br/>9000/9001]
        Redpanda[Redpanda<br/>9092]
    end

    subgraph Backend
        API[entitybase-backend<br/>8080]
        ID[idworker<br/>8001]
        Workers[Workers<br/>8002-8006]
    end

    subgraph Frontend
        Orch[orchestrator-frontend<br/>8080]
    end

    subgraph SSE
        SSE_BE[entitybase-sse-backend<br/>8888]
        SSE_FE[entitybase-sse-frontend<br/>8889]
    end

    Users((Users))

    Users -->|HTTP| Orch
    Users -->|HTTP| API
    Users -->|HTTP| SSE_BE
    Users -->|HTTP| SSE_FE

    Orch --> API

    API --> MySQL
    API --> Minio
    API --> Redpanda
    API --> ID

    ID --> MySQL

    Workers --> MySQL
    Workers --> Minio

    SSE_BE --> Redpanda
    SSE_FE --> Redpanda
```

## Quick Start

```bash
# Copy environment template
cp .env.example .env

# Build Docker images and start services
make run
```

## Dependencies

See [INSTALL.md](INSTALL.md) for installation instructions.

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make build` | Build all Docker images |
| `make run` | Build images and start all services |
| `make stop` | Stop all running services |
| `make remove` | Stop services and remove containers/volumes |
| `make clean` | Prune Docker system (containers, images, networks, build cache) |
| `make reset` | Reset entitybase data (runs reset.sh) |

## Manual Commands

```bash
# Build images
./build-images.sh

# Start services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose stop
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| mysql | 3306 | Database |
| minio | 9000, 9001 | S3 storage (API + console) |
| redpanda | 9092, 9644 | Kafka broker |
| redpanda-console | 8084 | Redpanda Console (Kafka UI) |
| entitybase-backend | 8080 | REST API |
| entitybase-sse-backend | 8888 | SSE API |
| entitybase-sse-frontend | 8889 | SSE Frontend |
| idworker | 8001 | ID generation |

## Profiles

- `core` - Infrastructure + main services (default)
- `workers` - Background job workers

```bash
# Start with workers
docker compose --profile workers up -d
```

## License

This project is licensed under the [GNU General Public License v3.0 or later](LICENSE).

## Environment Variables

See [INSTALL.md](INSTALL.md) for full list.
