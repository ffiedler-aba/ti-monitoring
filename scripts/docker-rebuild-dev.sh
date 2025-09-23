#!/usr/bin/env bash
set -euo pipefail

# Optional: Python venv aktivieren, falls vorhanden
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

# Projekt-Root relativ zu diesem Skript ermitteln
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Callback-Validierung (strict) – bricht bei Fehlern ab
if command -v python3 >/dev/null 2>&1; then
  echo "Running callback validation..."
  python3 "${REPO_ROOT}/scripts/validate_callbacks.py" --strict || {
    echo "Callback validation failed. Aborting rebuild." >&2
    exit 1
  }
fi

# Docker Rebuild + Up
GIT_TAG=$(git describe --tags --always 2>/dev/null || echo "")
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "")

docker compose -f docker-compose-dev.yml down && \
  docker compose -f docker-compose-dev.yml build \
    --build-arg TI_VERSION="$GIT_TAG" \
    --build-arg TI_COMMIT="$GIT_SHA" && \
  docker compose -f docker-compose-dev.yml up -d