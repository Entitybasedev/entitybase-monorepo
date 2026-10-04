# Meilisearch indexer worker

Keeps the Meilisearch entity index in step with the database, so the search page
has something to search.

Part of the Entitybase monorepo.

## How it works

1. Consumes entity change events from the `entity_change` topic
2. On a create or update, reads the entity's revision from MariaDB and resolves
   its labels, descriptions and aliases (terms are content-addressed, so the
   revision only holds hashes)
3. Indexes the resulting document into Meilisearch; removes it on a delete

Meilisearch holds one index with all entity types; each document carries its
`type`, which search filters on. The worker reads the database directly and
never calls the API.

## Layout

- `src/meilisearch_indexer_worker/` - worker code
- `tests/` - unit tests

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `MEILISEARCH_ENABLED` | `false` | The worker does nothing while this is false |
| `MEILISEARCH_HOST` | `localhost` | Meilisearch host |
| `MEILISEARCH_PORT` | `7700` | Meilisearch port |
| `MEILISEARCH_API_KEY` | empty | Meilisearch API key |
| `MEILISEARCH_INDEX` | `entitybase` | Index to write |
| `MEILISEARCH_CONSUMER_GROUP` | `entitybase-meilisearch-indexer` | Kafka consumer group |
| `MEILISEARCH_REINDEX_ON_START` | `false` | Index every existing entity on startup |
| `WORKER_ID` | generated | Worker identifier |
| `WORKER_PORT` | `8009` | Port of the health endpoint |

`MEILISEARCH_REINDEX_ON_START` is what makes a fresh instance searchable: the
index starts empty, so entities that exist before the worker starts would
otherwise never be indexed.

## Running

```bash
# tests
uv run pytest

# run (from the repository root, with the stack up)
MEILISEARCH_ENABLED=true python -m meilisearch_indexer_worker
```