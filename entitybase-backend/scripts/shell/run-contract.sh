#!/bin/bash
set -e
export PYTHONPATH=src
uv run pytest tests/contract/ -v -m contract
