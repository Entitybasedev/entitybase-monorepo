#!/bin/bash
cd "$(dirname "$0")/../.."
set -Eeuo pipefail

uv run python scripts/linters/check_logger_debug.py src/