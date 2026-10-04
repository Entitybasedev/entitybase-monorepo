# General stats worker

Recomputes the general statistics snapshot.

Part of the Entitybase monorepo. 


## Layout

- `src/general_stats_worker/` - worker code
- `tests/` - unit tests (`tests/integration/` where applicable)

## Running

The worker reads its configuration from the environment (the same variables
the backend uses) and talks to the database directly; it does not import or
call the API. It is disabled by default: `general_stats_enabled` must be set to `true`.

```bash
# tests
uv run pytest

# run (from the repository root, with the stack up)
general_stats_worker_enabled=true python -m general_stats_worker
```
