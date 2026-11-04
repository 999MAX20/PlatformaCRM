#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARCHIVE_NAME="${1:-zani-clean.zip}"
if [[ "$ARCHIVE_NAME" != *.zip || "$ARCHIVE_NAME" == */* || "$ARCHIVE_NAME" == *\\* || "$ARCHIVE_NAME" == .* || "$ARCHIVE_NAME" == -* ]]; then
  echo "Archive name must be a plain .zip filename, without a directory or leading dot/dash." >&2
  exit 2
fi
ARCHIVE_PATH="$ROOT_DIR/$ARCHIVE_NAME"
if [[ -L "$ARCHIVE_PATH" || -d "$ARCHIVE_PATH" ]]; then
  echo "Archive destination must not be a symlink or directory." >&2
  exit 2
fi
command -v rsync >/dev/null
command -v python3 >/dev/null
TMP_DIR="$(mktemp -d)"
trap 'rm -rf -- "$TMP_DIR"' EXIT

cd "$ROOT_DIR"
rsync -a --no-links --no-devices --no-specials ./ "$TMP_DIR/zani/" \
  --include=".env.example" \
  --include=".env.local.example" \
  --include=".env.staging.example" \
  --include=".env.production.example" \
  --include=".env.render.example" \
  --include=".env.chromatic.example" \
  --include="frontend/.env.example" \
  --include="frontend/.env.staging.example" \
  --include="frontend/.env.production.example" \
  --exclude=".git/" \
  --exclude=".[eE][nN][vV]" \
  --exclude=".[eE][nN][vV].*" \
  --exclude="*.[eE][nN][vV]" \
  --exclude="*.[eE][nN][vV].*" \
  --exclude="output/" \
  --exclude="backups/" \
  --exclude="backup/" \
  --exclude="logs/" \
  --exclude="private_media/" \
  --exclude=".playwright-cli/" \
  --exclude=".playwright/" \
  --exclude=".auth/" \
  --exclude="browser-profile/" \
  --exclude="chrome-profile/" \
  --exclude="user-data-dir/" \
  --exclude="storage-state*.json" \
  --exclude="storage_state*.json" \
  --exclude="storageState*.json" \
  --exclude="*.storage-state.json" \
  --exclude="session.json" \
  --exclude="session-*.json" \
  --exclude="cookies*.json" \
  --exclude="*.har" \
  --exclude="*.[sS][qQ][lL][iI][tT][eE]*" \
  --exclude="*.[dD][bB]" \
  --exclude="*.[dD][bB]-*" \
  --exclude="*.[dD][uU][mM][pP]" \
  --exclude="*.[bB][aA][kK]" \
  --exclude=".venv/" \
  --exclude="venv/" \
  --exclude="node_modules/" \
  --exclude="frontend/node_modules/" \
  --exclude="frontend/dist/" \
  --exclude="dist/" \
  --exclude="build/" \
  --exclude="db.sqlite3" \
  --exclude="media/" \
  --exclude="staticfiles/" \
  --exclude="test-results/" \
  --exclude="playwright-report/" \
  --exclude="coverage/" \
  --exclude=".coverage" \
  --exclude="__MACOSX/" \
  --exclude=".DS_Store" \
  --exclude="__pycache__/" \
  --exclude="*.pyc" \
  --exclude="*.pyo" \
  --exclude="*.log" \
  --exclude="*.zip" \
  --exclude="*.tsbuildinfo" \
  --exclude=".pytest_cache/" \
  --exclude=".mypy_cache/" \
  --exclude=".ruff_cache/" \
  --exclude="htmlcov/" \
  --exclude="$ARCHIVE_NAME"

(cd "$TMP_DIR" && python3 -m zipfile -c "$TMP_DIR/archive.zip" zani)
mv -- "$TMP_DIR/archive.zip" "$ARCHIVE_PATH"

echo "Created clean archive: $ARCHIVE_PATH"
