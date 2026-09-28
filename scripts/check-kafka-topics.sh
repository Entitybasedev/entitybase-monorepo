#!/bin/bash
# Script to check Kafka/Redpanda topic messages

echo "=== Checking entity_change topic ==="
docker exec redpanda rpk topic consume entity_change --num 10 2>&1 || echo "No messages or error"
