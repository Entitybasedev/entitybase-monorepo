#!/bin/bash
cd "$(dirname "$0")/../.."
set -Eeuo pipefail

uv run ruff check --fix --exit-non-zero-on-fix src/ tests/ # scripts/
uv run ruff format src/ tests/ # scripts/
