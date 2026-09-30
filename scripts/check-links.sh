#!/usr/bin/env bash
# Link checker: zero 404s (or other 4xx/5xx) = green.
# Modes:
#   ./scripts/check-links.sh docs [base-url]   - crawl the docs sitemap
#   ./scripts/check-links.sh frontend [base]   - check the frontend/API routes
set -u

MODE="${1:-}"
BASE="${2:-}"

if [ -t 1 ]; then
    GREEN=$'\033[32m'; RED=$'\033[31m'; DIM=$'\033[2m'; RESET=$'\033[0m'
else
    GREEN=""; RED=""; DIM=""; RESET=""
fi

FAILURES=0
CHECKED=0

check_url() {
    local url="$1"
    local code
    code=$(timeout 10 curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    CHECKED=$((CHECKED + 1))
    if [ "$code" -ge 200 ] && [ "$code" -lt 400 ]; then
        printf "${GREEN}✓ %s${RESET}  %s\n" "$code" "$url"
    else
        FAILURES=$((FAILURES + 1))
        printf "${RED}✗ %s${RESET}  %s\n" "$code" "$url"
    fi
}

case "$MODE" in
    docs)
        BASE="${BASE:-https://entitybasedev.github.io/entitybase-monorepo}"
        echo "Checking docs site: $BASE"
        echo ""
        sitemap=$(timeout 15 curl -sf "$BASE/sitemap.xml" 2>/dev/null)
        if [ -z "$sitemap" ]; then
            echo "✗ could not fetch sitemap: $BASE/sitemap.xml"
            exit 1
        fi
        # Extract <loc> URLs from the sitemap and check each page
        while read -r url; do
            check_url "$url"
        done < <(echo "$sitemap" | grep -o '<loc>[^<]*</loc>' | sed 's/<loc>//;s/<\/loc>//')
        ;;
    frontend)
        BASE="${BASE:-http://localhost:8080}"
        echo "Checking frontend routes: $BASE"
        echo ""
        for route in / /docs /k2s/docs /openapi.json /health; do
            check_url "$BASE$route"
        done
        ;;
    *)
        echo "usage: $0 docs|frontend [base-url]"
        exit 2
        ;;
esac

echo ""
if [ "$FAILURES" -eq 0 ]; then
    printf "${GREEN}${CHECKED}/${CHECKED} links OK${RESET}\n"
    exit 0
else
    printf "${RED}${CHECKED}/${CHECKED} links checked - ${FAILURES} failing${RESET}\n"
    exit 1
fi
