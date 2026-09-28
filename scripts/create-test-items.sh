#!/bin/bash

API_URL="${API_URL:-http://localhost:8083}"
COUNT="${1:-5}"
SLEEP_SECONDS="${2:-1}"

echo "Creating $COUNT items with $SLEEP_SECONDS second(s) sleep between each..."

for i in $(seq 1 "$COUNT"); do
    echo "Creating item $i..."
    response=$(curl -s -X POST "$API_URL/v1/entitybase/entities/items" \
        -H "X-User-ID: 1" \
        -H "X-Edit-Summary: Test item $i for change stream")
    
    if echo "$response" | grep -q '"success":true'; then
        entity_id=$(echo "$response" | grep -oP '"entity_id":"[^"]+' | cut -d'"' -f4)
        echo "  Created: $entity_id"
    else
        echo "  Error: $response"
    fi
    
    if [ "$i" -lt "$COUNT" ]; then
        sleep "$SLEEP_SECONDS"
    fi
done

echo "Done!"
