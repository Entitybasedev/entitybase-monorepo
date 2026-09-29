#!/bin/bash
set -e

NO_CACHE=""
if [ "$1" = "--no-cache" ]; then
    NO_CACHE="--no-cache"
fi

cd "$(dirname "$0")/.."

echo "=========================================="
echo "Building Docker images for Entitybase"
echo "=========================================="

echo ""
echo "[api] Building entitybase-api:latest..."
docker build $NO_CACHE -t entitybase-api:latest \
    -f entitybase-backend/docker/containers/Dockerfile.api entitybase-backend/

echo ""
echo "[kafka2sse] Building kafka2sse-backend:latest..."
docker build $NO_CACHE -t kafka2sse-backend:latest kafka2sse-backend/

echo ""
echo "All images built."
