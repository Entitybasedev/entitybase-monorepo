# Development

## Backend (entitybase-backend)

```bash
cd entitybase-backend
uv sync --group dev
just lint        # ruff, mypy, radon + custom linters
just test-unit   # unit tests
```

## Frontend (entitybase-frontend)

```bash
cd entitybase-frontend
npm install
npm test         # vitest unit tests (single worker)
npm run dev      # http://localhost:8085 (proxies to the docker API)
```

## E2E tests (e2e-ui)

```bash
just e2e-mock    # Playwright e2e against mock backends (no docker)
just e2e         # Playwright e2e against the running docker stack
```

The e2e suite covers item/property/lexeme creation through the UI,
statements, and the change stream (an event produced for a created
item must appear in the stream tab).

## CI

GitHub Actions run lint + unit/contract/integration tests per backend,
frontend unit tests, and the Playwright e2e suite against the real
docker stack. See `.github/workflows/ci.yml`.
