#!/bin/bash
cd "$(dirname "$0")/../.."
set -e

echo "Exporting uv dependencies to requirements files..."

uv export --format requirements-txt --no-hashes --no-dev --no-emit-project -o requirements.txt

echo "Requirements files updated successfully"
