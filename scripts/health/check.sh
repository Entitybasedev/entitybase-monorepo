#!/usr/bin/env bash
# Health check for the Entitybase docker stack.
# Exits non-zero if any service is unhealthy.

cd "$(dirname "$0")/../.."

FAILURES=0
ANY_RUNNING=0

if ! timeout 10 docker info > /dev/null 2>&1; then
    echo "✗ docker is not running"
    exit 1
fi

# Single fast snapshot of running containers (avoids compose-level locks)
RUNNING_CONTAINERS=$(timeout 15 docker ps --filter status=running --format '{{.Names}}' 2>/dev/null)

is_running() {
    echo "$RUNNING_CONTAINERS" | grep -qx "$1"
}

# TTY-aware colors
if [ -t 1 ]; then
    GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'; DIM=$'\033[2m'; RESET=$'\033[0m'
else
    GREEN=""; RED=""; YELLOW=""; DIM=""; RESET=""
fi

start_check() {
    # Progress: print the service name before running its check
    printf "%-22s " "$1"
}

report() {
    local status="$1" detail="$2"
    case "$status" in
        healthy)     printf "${GREEN}✓ healthy${RESET}" ;;
        running)     printf "${GREEN}✓ running${RESET}" ;;
        not-running) printf "${RED}✗ not running${RESET}" ;;
        *)           printf "${RED}✗ unhealthy${RESET}" ;;
    esac
    [ -n "$detail" ] && printf "  ${DIM}%s${RESET}" "$detail"
    printf "\n"
}

fail() {
    FAILURES=$((FAILURES + 1))
    report "$1" unhealthy "$2"
}

# --- mysql ---
start_check "mysql"
if is_running mysql; then
    ANY_RUNNING=1
    if timeout 10 docker compose exec -T mysql mysqladmin ping -h localhost --silent > /dev/null 2>&1; then
        report healthy
    else
        fail "mysql" "mysqladmin ping failed"
    fi
else
    report "mysql" not-running
    FAILURES=$((FAILURES + 1))
fi

# --- valkey ---
start_check "valkey"
if is_running valkey; then
    ANY_RUNNING=1
    if timeout 10 docker compose exec -T valkey valkey-cli ping 2>/dev/null | grep -q PONG; then
        report healthy
    else
        fail "valkey" "valkey-cli ping failed"
    fi
else
    report "valkey" not-running
    FAILURES=$((FAILURES + 1))
fi

# --- redpanda ---
start_check "redpanda"
if is_running redpanda; then
    ANY_RUNNING=1
    if timeout 10 docker compose exec -T redpanda rpk cluster health 2>/dev/null | grep -q Healthy; then
        report healthy
    else
        fail "redpanda" "cluster not healthy"
    fi
else
    report "redpanda" not-running
    FAILURES=$((FAILURES + 1))
fi

# --- entitybase-api ---
if is_running entitybase-api; then
    ANY_RUNNING=1
    api_health=$(timeout 10 curl -sf http://localhost:8083/health 2>/dev/null)
    if [ -n "$api_health" ]; then
        status=$(echo "$api_health" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        s3=$(echo "$api_health" | grep -o '"s3":"[^"]*"' | cut -d'"' -f4)
        db=$(echo "$api_health" | grep -o '"vitess":"[^"]*"' | cut -d'"' -f4)
        report healthy "status=$status db=$db s3=$s3"
    else
        fail "entitybase-api" "health endpoint not responding on :8083"
    fi
else
    report "entitybase-api" not-running
    FAILURES=$((FAILURES + 1))
fi

# --- kafka2sse-backend ---
if is_running kafka2sse-backend; then
    ANY_RUNNING=1
    k2s_health=$(timeout 10 curl -sf http://localhost:8888/health 2>/dev/null)
    if [ -n "$k2s_health" ]; then
        kstatus=$(echo "$k2s_health" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        kkafka=$(echo "$k2s_health" | grep -o '"kafka":"[^"]*"' | cut -d'"' -f4)
        report healthy "status=$kstatus kafka=$kkafka"
    else
        fail "kafka2sse-backend" "health endpoint not responding on :8888"
    fi
else
    report "kafka2sse-backend" not-running
    FAILURES=$((FAILURES + 1))
fi

# --- entitybase-frontend ---
if is_running entitybase-frontend; then
    ANY_RUNNING=1
    if timeout 10 curl -sf http://localhost:8080/ > /dev/null 2>&1; then
        report running
    else
        fail "entitybase-frontend" "not responding on :8080"
    fi
else
    report "entitybase-frontend" not-running
    FAILURES=$((FAILURES + 1))
fi

echo ""
TOTAL=6
HEALTHY=$((TOTAL - FAILURES))
if [ "$FAILURES" -eq 0 ]; then
    echo "${GREEN}${HEALTHY}/${TOTAL} healthy${RESET}"
    exit 0
elif [ "$ANY_RUNNING" -eq 0 ]; then
    echo "${YELLOW}0/${TOTAL} healthy - stack is not running (try: just up)${RESET}"
    exit 1
else
    echo "${RED}${HEALTHY}/${TOTAL} healthy - ${FAILURES} failing${RESET}"
    exit 1
fi
