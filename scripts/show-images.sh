#!/bin/bash
cd "$(dirname "$0")/.."

echo "=== Entitybase Docker Images ==="
docker images | grep -E "entitybase-" | head -20 || echo "No entitybase images found"
