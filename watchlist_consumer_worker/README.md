# Watchlist consumer worker

Consumes entity changes and updates watchlists.

Part of the Entitybase monorepo. 


## Layout

- `src/watchlist_consumer_worker/` - worker code
- `tests/` - unit tests (`tests/integration/` where applicable)

## Running

The worker reads its configuration from the environment (the same variables
the backend uses) and talks to the database directly; it does not import or
call the API. It is disabled by default: `enabled` must be set to `true`.

```bash
# tests
uv run pytest

# run (from the repository root, with the stack up)
watchlist_consumer_worker_enabled=true python -m watchlist_consumer_worker
```
