#!/bin/bash
cd "$(dirname "$0")/../.."
set -Eeuo pipefail

echo "Checking for tuple() usage..."

uv run python scripts/linters/check_tuple_usage.py src/

echo "Tuple usage linting passed!"