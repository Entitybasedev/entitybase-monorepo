#!/bin/bash
# Assemble the docs site: monorepo pages + the backend's existing docs,
# then build with mkdocs. Requires mkdocs-material (pip install mkdocs-material).
set -e

cd "$(dirname "$0")/.."

SITE_DOCS=".docs-site/docs"

rm -rf "$SITE_DOCS" .docs-site/site
mkdir -p "$SITE_DOCS"

# Monorepo pages
cp docs-src/*.md "$SITE_DOCS/"

# Backend docs (kept in the backend repo; copied at build time)
mkdir -p "$SITE_DOCS/backend"
cp -r entitybase-backend/docs/. "$SITE_DOCS/backend/"
cp entitybase-backend/ENDPOINTS.md entitybase-backend/FAQ.md \
   entitybase-backend/DEVELOPMENT.md "$SITE_DOCS/backend/"

MKDOCS="${MKDOCS:-mkdocs}"
if ! command -v "$MKDOCS" > /dev/null 2>&1; then
    # fall back to the backend venv (mkdocs-material lives in its dev group)
    if [ -x entitybase-backend/.venv/bin/mkdocs ]; then
        MKDOCS="entitybase-backend/.venv/bin/mkdocs"
    fi
fi
"$MKDOCS" build

echo ""
echo "Docs built to site/"
