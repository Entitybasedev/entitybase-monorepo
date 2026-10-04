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
echo "[meilisearch-indexer-worker] Building meilisearch-indexer-worker:latest..."
docker build $NO_CACHE -t meilisearch-indexer-worker:latest \
    -f meilisearch_indexer_worker/Dockerfile .

echo ""
echo "[frontend] Building entitybase-frontend:latest..."
docker build $NO_CACHE -t entitybase-frontend:latest entitybase-frontend/

echo ""
echo "All images built."
