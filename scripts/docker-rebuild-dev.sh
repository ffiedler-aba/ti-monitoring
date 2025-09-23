#!/usr/bin/env bash
set -euo pipefail

# Optional: Python venv aktivieren, falls vorhanden
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

# Projekt-Root relativ zu diesem Skript ermitteln
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Optionaler Schalter: --full|--rebuild erzwingt kompletten Rebuild und Neustart
if [[ "${1:-}" =~ ^(--full|--rebuild)$ ]]; then
  echo "Vollständiger Rebuild per Schalter (${1}) angefordert."
  GIT_TAG=$(git describe --tags --always 2>/dev/null || echo "")
  GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "")
  docker compose -f docker-compose-dev.yml down || true
  docker compose -f docker-compose-dev.yml build \
    --build-arg TI_VERSION="$GIT_TAG" \
    --build-arg TI_COMMIT="$GIT_SHA"
  docker compose -f docker-compose-dev.yml up -d
  exit 0
fi

# Callback-Validierung (strict) – bricht bei Fehlern ab
if command -v python3 >/dev/null 2>&1; then
  echo "Running callback validation..."
  python3 "${REPO_ROOT}/scripts/validate_callbacks.py" --strict || {
    echo "Callback validation failed. Aborting rebuild." >&2
    exit 1
  }
fi

# Smart dev rebuild
# 1) Wenn requirements/Dockerfile unverändert: nur Quellcode synchronisieren und Services neustarten
# 2) Sonst: vollständiger Build

GIT_TAG=$(git describe --tags --always 2>/dev/null || echo "")
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "")

HASH_INPUTS=""
for f in Dockerfile requirements.txt requirements-dev.txt; do
  if [ -f "$REPO_ROOT/$f" ]; then
    HASH_INPUTS+=$(sha256sum "$REPO_ROOT/$f" | awk '{print $1}')
  fi
done
BUILD_HASH=$(printf "%s" "$HASH_INPUTS" | sha256sum | awk '{print $1}')
CACHE_DIR="$REPO_ROOT/.cache"
mkdir -p "$CACHE_DIR"
CACHE_FILE="$CACHE_DIR/dev-build.hash"
PREV_HASH=""
if [ -f "$CACHE_FILE" ]; then PREV_HASH=$(cat "$CACHE_FILE" || true); fi

fast_sync() {
  echo "Fast-sync geänderte Quellen in laufende Container..."
  # Stelle sicher, dass Services laufen
  docker compose -f docker-compose-dev.yml up -d

  # Liste der zu kopierenden Dateien (tracked + untracked, aber .gitignored ausschließen)
  # WICHTIG: Null-terminiert, um Pfade mit Leerzeichen korrekt zu handhaben
  TMP_LIST=$(mktemp)
  (cd "$REPO_ROOT" && git ls-files -co -z --exclude-standard) > "$TMP_LIST"

  # Tar-Stream erstellen und im Container auf /app entpacken (Null-terminierte Liste)
  # Web
  if docker compose -f docker-compose-dev.yml ps ti-monitoring-web >/dev/null 2>&1; then
    tar -C "$REPO_ROOT" -cf - --null -T "$TMP_LIST" | docker compose -f docker-compose-dev.yml exec -T ti-monitoring-web sh -lc "tar -C /app -xf -"
  fi
  # Cron
  if docker compose -f docker-compose-dev.yml ps ti-monitoring-cron >/dev/null 2>&1; then
    tar -C "$REPO_ROOT" -cf - --null -T "$TMP_LIST" | docker compose -f docker-compose-dev.yml exec -T ti-monitoring-cron sh -lc "tar -C /app -xf -"
  fi
  rm -f "$TMP_LIST"

  # Services sanft neustarten, Requirements unverändert
  docker compose -f docker-compose-dev.yml restart ti-monitoring-web ti-monitoring-cron
}

full_build() {
  echo "Änderungen an Abhängigkeiten erkannt → vollständiger Build"
  docker compose -f docker-compose-dev.yml down || true
  docker compose -f docker-compose-dev.yml build \
    --build-arg TI_VERSION="$GIT_TAG" \
    --build-arg TI_COMMIT="$GIT_SHA"
  docker compose -f docker-compose-dev.yml up -d
  echo "$BUILD_HASH" > "$CACHE_FILE"
}

if [ -n "$PREV_HASH" ] && [ "$PREV_HASH" = "$BUILD_HASH" ]; then
  fast_sync
else
  full_build
fi