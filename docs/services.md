# Running the stack

## Quick Start

```bash
# Build Docker images and start the whole stack
just up

# Check the health of all services
just health

# Service URLs
just docker-help
```

`just up` creates `.env` from `env.example` on first run, builds the
images, starts the stack and waits for the API to become healthy.

## Service URLs

| Service | URL |
|---------|-----|
| UI (entities + change stream) | http://localhost:8080 |
| API | http://localhost:8083 |
| API docs (OpenAPI) | http://localhost:8083/docs |
| Stream backend topics | http://localhost:8888/v1/topics |

## Just Commands

| Command | Description |
|---------|-------------|
| `just up` | Build images and start the whole stack |
| `just down` | Stop the stack |
| `just down-v` | Stop the stack and remove volumes (fresh database) |
| `just logs` | Follow logs from all services |
| `just health` | Health table for all services (exit 1 on failure) |
| `just docker-help` | Print the service URLs |
| `just e2e` | Playwright e2e against the running stack |
| `just e2e-mock` | Playwright e2e against mock backends (no docker) |
| `just frontend` | Run the frontend dev server |
