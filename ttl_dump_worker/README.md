# TTL dump worker

Writes periodic TTL dumps of the entity store.

Part of the Entitybase monorepo. 
Writes dumps to the S3-compatible object store (rustfs).


## Layout

- `src/ttl_dump_worker/` - worker code
- `tests/` - unit tests (`tests/integration/` where applicable)

## Running

The worker reads its configuration from the environment (the same variables
the backend uses) and talks to the database directly; it does not import or
call the API. It is disabled by default: `ttl_dump_enabled` must be set to `true`.

```bash
# tests
uv run pytest

# run (from the repository root, with the stack up)
ttl_dump_worker_enabled=true python -m ttl_dump_worker
```
