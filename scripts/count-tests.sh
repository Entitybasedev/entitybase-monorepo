#!/bin/bash
# Repo-wide test counts: backend (pytest), change-stream backend (pytest),
# frontend (vitest) and e2e-ui (Playwright).
cd "$(dirname "$0")/.."
set -e

echo "# Test Counts"

# --- entitybase-backend: pytest unit / integration / contract ---
echo "## entitybase-backend"
BACKEND_OVERALL=$(
  (cd entitybase-backend && uv run pytest --collect-only -q tests/unit tests/integration tests/contract 2>/dev/null \
    | grep -oP '\d+(?= tests collected)') || echo "0"
)
BACKEND_UNIT=$(grep -rE "^\s*(async )?def test_" entitybase-backend/tests/unit --include="*.py" | wc -l)
BACKEND_INTEGRATION=$(grep -rE "^\s*(async )?def test_" entitybase-backend/tests/integration --include="*.py" | wc -l)
BACKEND_CONTRACT=$(grep -rE "^\s*(async )?def test_" entitybase-backend/tests/contract --include="*.py" | wc -l)
echo "- Overall (pytest): $BACKEND_OVERALL"
echo "- Unit: $BACKEND_UNIT"
echo "- Integration: $BACKEND_INTEGRATION"
echo "- Contract: $BACKEND_CONTRACT"
echo ""

# --- kafka2sse-backend: pytest unit / integration / contract ---
echo "## kafka2sse-backend"
K2S_OVERALL=$(
  (cd kafka2sse-backend && uv run pytest --collect-only -q tests/unit tests/integration tests/contract 2>/dev/null \
    | grep -oP '\d+(?= tests collected)') || echo "0"
)
K2S_UNIT=$(grep -rE "^\s*(async )?def test_" kafka2sse-backend/tests/unit --include="*.py" | wc -l)
K2S_INTEGRATION=$(grep -rE "^\s*(async )?def test_" kafka2sse-backend/tests/integration --include="*.py" | wc -l)
K2S_CONTRACT=$(grep -rE "^\s*(async )?def test_" kafka2sse-backend/tests/contract --include="*.py" | wc -l)
echo "- Overall (pytest): $K2S_OVERALL"
echo "- Unit: $K2S_UNIT"
echo "- Integration: $K2S_INTEGRATION"
echo "- Contract: $K2S_CONTRACT"
echo ""

# --- entitybase-frontend: vitest ---
echo "## entitybase-frontend"
FRONTEND_TESTS=$(grep -rcE "^\s*(it|test)\(" entitybase-frontend/src/__tests__ --include="*.test.js" \
  | awk -F: '{sum += $2} END {print sum}')
FRONTEND_FILES=$(ls entitybase-frontend/src/__tests__/*.test.js 2>/dev/null | wc -l)
echo "- Tests (vitest): $FRONTEND_TESTS"
echo "- Files: $FRONTEND_FILES"
echo ""

# --- e2e-ui: Playwright ---
echo "## e2e-ui"
E2E_TESTS=$(grep -rcE "^\s*test\(" e2e-ui/tests --include="*.spec.js" \
  | awk -F: '{sum += $2} END {print sum}')
E2E_FILES=$(ls e2e-ui/tests/*.spec.js 2>/dev/null | wc -l)
echo "- Tests (Playwright): $E2E_TESTS"
echo "- Files: $E2E_FILES"
echo ""

# --- Total ---
TOTAL=$((BACKEND_OVERALL + K2S_OVERALL + FRONTEND_TESTS + E2E_TESTS))
echo "- Total: $TOTAL"
echo ""
