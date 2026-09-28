#!/bin/bash
cd "$(dirname "$0")/../.."
set -e

echo "Exporting uv dependencies to requirements files..."

uv export --format requirements.txt --output requirements.txt --no-hashes --no-dev
uv export --format requirements.txt --output requirements-dev.txt --no-hashes --group dev
uv export --format requirements.txt --output requirements-idworker.txt --no-hashes --no-dev --group idworker
uv export --format requirements.txt --output requirements-stats-worker.txt --no-hashes --no-dev --group stats-worker
uv export --format requirements.txt --output requirements-json-worker.txt --no-hashes --no-dev --group json-worker
uv export --format requirements.txt --output requirements-ttl-worker.txt --no-hashes --no-dev --group ttl-worker

echo "Requirements files updated successfully"
