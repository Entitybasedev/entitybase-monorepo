# Entitybase monorepo recipes

API_URL := "http://localhost:8083"
FRONTEND_PORT := "8085"
MOCK_API_LOG := "/tmp/entitybase-mock-api.log"
MOCK_API_SCRIPT := "/tmp/entitybase-mock-api.mjs"

# Show available recipes
default:
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
    cd e2e-ui && API_URL={{API_URL}} E2E_MOCK=1 npx playwright test

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
    @curl -sf http://localhost:8888/health > /dev/null && echo "mock stream backend up on :8888" || (echo "mock stream backend failed:" && cat /tmp/entitybase-mock-stream.log && exit 1)

# Start the mock API in the background
mock-api-up:
    just -f {{justfile()}} mock-api-down
    @cp -f scripts/dev/mock-api.mjs {{MOCK_API_SCRIPT}}
    @nohup node {{MOCK_API_SCRIPT}} > {{MOCK_API_LOG}} 2>&1 & disown
    @sleep 1
    @curl -sf {{API_URL}}/health > /dev/null 2>&1 || curl -sf -X POST {{API_URL}}/v1/users -d '{"user_id":0}' > /dev/null 2>&1 && echo "mock API up on :8083" || (echo "mock API failed to start:" && cat {{MOCK_API_LOG}} && exit 1)

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
