#!/bin/bash
cd "$(dirname "$0")/../.."
uv run vulture --config pyproject.toml src config/linters/allowlists/vulture.txt
