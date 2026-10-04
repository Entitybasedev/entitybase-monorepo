# Incremental RDF worker

Emits incremental RDF diffs to the stream.

Part of the Entitybase monorepo. 


## Layout

- `src/incremental_rdf_worker/` - worker code
- `tests/` - unit tests (`tests/integration/` where applicable)

## Running

The worker reads its configuration from the environment (the same variables
the backend uses) and talks to the database directly; it does not import or
call the API. It is disabled by default: `incremental_rdf_enabled` must be set to `true`.

```bash
# tests
uv run pytest

# run (from the repository root, with the stack up)
incremental_rdf_worker_enabled=true python -m incremental_rdf_worker
```
