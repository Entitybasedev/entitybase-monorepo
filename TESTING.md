# Testing

## Create Test Items

Create items via the API to test change streams:

```bash
# Default: 5 items, 1s sleep between each
./scripts/create-test-items.sh

# Custom count and sleep
./scripts/create-test-items.sh 10 2

# Custom API URL
API_URL=http://localhost:8083 ./scripts/create-test-items.sh
```
