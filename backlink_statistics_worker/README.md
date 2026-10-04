# Backlink statistics worker

Recomputes backlink statistics on a schedule.

Part of the Entitybase monorepo. 


## Layout

- `src/backlink_statistics_worker/` - worker code
- `tests/` - unit tests (`tests/integration/` where applicable)

## Running

The worker reads its configuration from the environment (the same variables
the backend uses) and talks to the database directly; it does not import or
call the API. It is disabled by default: `backlink_stats_enabled` must be set to `true`.

```bash
# tests
uv run pytest

# run (from the repository root, with the stack up)
backlink_statistics_worker_enabled=true python -m backlink_statistics_worker
```
