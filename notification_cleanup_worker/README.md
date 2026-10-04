# Notification cleanup worker

Expires old user notifications.

Part of the Entitybase monorepo. 


## Layout

- `src/notification_cleanup_worker/` - worker code
- `tests/` - unit tests (`tests/integration/` where applicable)

## Running

The worker reads its configuration from the environment (the same variables
the backend uses) and talks to the database directly; it does not import or
call the API. It is disabled by default: `enabled` must be set to `true`.

```bash
# tests
uv run pytest

# run (from the repository root, with the stack up)
notification_cleanup_worker_enabled=true python -m notification_cleanup_worker
```
