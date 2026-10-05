#!/bin/bash
cd "$(dirname "$0")/../.."
set -e

echo "Running JSON lint: Detecting json.dumps usage and recommending model_dump(mode='json')"

uv run python scripts/linters/check_json_dumps.py src/