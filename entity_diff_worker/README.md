# Entity diff worker

Builds entity diffs from revision changes.

Part of the Entitybase monorepo. 


## Layout

- `src/entity_diff_worker/` - worker code
- `tests/` - unit tests (`tests/integration/` where applicable)

## Running

The worker reads its configuration from the environment (the same variables
the backend uses) and talks to the database directly; it does not import or
call the API. It is disabled by default: `enabled` must be set to `true`.

```bash
# tests
uv run pytest

# run (from the repository root, with the stack up)
entity_diff_worker_enabled=true python -m entity_diff_worker
```
