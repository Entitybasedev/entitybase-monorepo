# Elasticsearch indexer worker

Indexes entities into Elasticsearch.

Part of the Entitybase monorepo. 


## Layout

- `src/elasticsearch_indexer_worker/` - worker code
- `tests/` - unit tests (`tests/integration/` where applicable)

## Running

The worker reads its configuration from the environment (the same variables
the backend uses) and talks to the database directly; it does not import or
call the API. It is disabled by default: `elasticsearch_enabled` must be set to `true`.

```bash
# tests
uv run pytest

# run (from the repository root, with the stack up)
elasticsearch_indexer_worker_enabled=true python -m elasticsearch_indexer_worker
```
