# JSON dump worker

Writes periodic JSON dumps of the entity store.

Part of the Entitybase monorepo. 
Writes dumps to the S3-compatible object store (rustfs).


## Layout

- `src/json_dump_worker/` - worker code
- `tests/` - unit tests (`tests/integration/` where applicable)

## Running

The worker reads its configuration from the environment (the same variables
the backend uses) and talks to the database directly; it does not import or
call the API. It is disabled by default: `json_dump_enabled` must be set to `true`.

```bash
# tests
uv run pytest

# run (from the repository root, with the stack up)
json_dump_worker_enabled=true python -m json_dump_worker
```
