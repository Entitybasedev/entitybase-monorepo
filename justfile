# Entitybase monorepo recipes

API_URL := "http://localhost:8083"
FRONTEND_PORT := "8085"
# Mock servers use the 90xx range so they never collide with the docker stack
MOCK_API_URL := "http://localhost:9083"
MOCK_STREAM_URL := "http://localhost:9088"
MOCK_API_LOG := "/tmp/entitybase-mock-api.log"
MOCK_API_SCRIPT := "/tmp/entitybase-mock-api.mjs"

# Show available recipes
default:
    @just --list

# Show available recipes (same as running just without arguments)
help:
    @just --list

# --- E2E (Playwright) ---

# Run e2e tests against a running stack (real or mock API at :8083)
e2e:
    just -f {{justfile()}} e2e-install
    cd e2e-ui && API_URL={{API_URL}} npx playwright test

# Run e2e tests against throwaway mock backends (no docker/backend needed)
e2e-mock:
    just -f {{justfile()}} mock-api-up
    just -f {{justfile()}} mock-stream-up
    cd e2e-ui && API_URL={{MOCK_API_URL}} STREAM_TARGET={{MOCK_STREAM_URL}} E2E_MOCK=1 npx playwright test

# Stop the mock backends
mock-api-down:
    -pkill -f entitybase-mock-api || true
    -pkill -f entitybase-mock-stream || true

# Start the mock stream backend in the background
mock-stream-up:
    -pkill -f entitybase-mock-stream || true
    @cp -f scripts/dev/mock-stream-api.mjs /tmp/entitybase-mock-stream.mjs
    @nohup node /tmp/entitybase-mock-stream.mjs > /tmp/entitybase-mock-stream.log 2>&1 & disown
    @sleep 1
    @curl -sf {{MOCK_STREAM_URL}}/health > /dev/null && echo "mock stream backend up on :9088" || (echo "mock stream backend failed:" && cat /tmp/entitybase-mock-stream.log && exit 1)

# Start the mock API in the background
mock-api-up:
    just -f {{justfile()}} mock-api-down
    @cp -f scripts/dev/mock-api.mjs {{MOCK_API_SCRIPT}}
    @nohup node {{MOCK_API_SCRIPT}} > {{MOCK_API_LOG}} 2>&1 & disown
    @sleep 1
    @curl -sf {{MOCK_API_URL}}/health > /dev/null 2>&1 || curl -sf -X POST {{MOCK_API_URL}}/v1/users -d '{"user_id":0}' > /dev/null 2>&1 && echo "mock API up on :9083" || (echo "mock API failed to start:" && cat {{MOCK_API_LOG}} && exit 1)

# Install playwright + frontend deps
e2e-install:
    cd e2e-ui && npm install --silent
    cd entitybase-frontend && npm install --silent

# --- Frontend ---

# Run the entitybase frontend dev server (proxies /v1 to :8083)
frontend:
    cd entitybase-frontend && npm install --silent && npm run dev

# Build the frontend
frontend-build:
    cd entitybase-frontend && npm install --silent && npm run build

# --- Full docker stack ---

# Build images and start the whole stack (infra + api + stream backend)
up:
    #!/usr/bin/env bash
    set -e
    [ -f .env ] || (cp env.example .env && echo "Created .env from env.example")
    ./scripts/build-images.sh
    docker compose up -d --remove-orphans --wait
    echo "Waiting for the api to become healthy..."
    for i in $(seq 1 60); do
        if curl -sf http://localhost:8083/health > /dev/null; then
            echo ""
            echo "Entitybase is running."
            just docker-help
            exit 0
        fi
        sleep 3
    done
    echo "api did not become healthy; recent logs:"
    docker compose logs --tail=50 entitybase-api
    exit 1

# Stop the stack
down:
    docker compose down

# Stop the stack and remove volumes (fresh database)
down-v:
    docker compose down -v

# Check links on the running docker stack (zero 404s = green)
check:
    ./scripts/check-links.sh frontend

# Check all links on the deployed docs site
check-docs:
    ./scripts/check-links.sh docs

# Show health of all docker services
health:
    timeout 120 ./scripts/health/check.sh

# Workers live in their own top-level directories, one project each
WORKER_DIRS := "backlink_statistics_worker elasticsearch_indexer_worker entity_diff_worker general_stats_worker incremental_rdf_worker json_dump_worker notification_cleanup_worker ttl_dump_worker user_stats_worker watchlist_consumer_worker"

# Test every worker (each is a standalone project next to the backend)
test-workers:
    #!/usr/bin/env bash
    for worker in {{WORKER_DIRS}}; do
        echo "== $worker"
        (cd "$worker" && uv run pytest -q) || exit 1
    done

# Repo statistics (currently: test counts only)
statistics:
    ./scripts/count-tests.sh

# Build the documentation site (requires mkdocs-material)
docs:
    #!/usr/bin/env bash
    MKDOCS="${MKDOCS:-mkdocs}"
    if ! command -v "$MKDOCS" > /dev/null 2>&1; then
        if [ -x entitybase-backend/.venv/bin/mkdocs ]; then
            MKDOCS="entitybase-backend/.venv/bin/mkdocs"
        fi
    fi
    "$MKDOCS" build

# Show the URLs of the running docker services
docker-help:
    @echo "Entitybase docker stack:"
    @echo "  UI:              http://localhost:8080"
    @echo "  API:             http://localhost:8083"
    @echo "  API docs:        http://localhost:8083/docs"
    @echo "  Stream backend:  http://localhost:8888/v1/topics"
    @echo "  Health check:    just health"

# Follow logs from all services
logs:
    docker compose logs -f --tail=100
