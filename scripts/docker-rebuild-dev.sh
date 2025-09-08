#!/usr/bin/env bash
set -euo pipefail

# Optional: Python venv aktivieren, falls vorhanden
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

# Callback-Validierung (strict) – bricht bei Fehlern ab
if command -v python3 >/dev/null 2>&1; then
  echo "Running callback validation..."
  python3 validate_callbacks.py --strict || {
    echo "Callback validation failed. Aborting rebuild." >&2
    exit 1
  }
fi

# Docker Rebuild + Up
docker compose -f docker-compose-dev.yml down && \
  docker compose -f docker-compose-dev.yml build && \
  docker compose -f docker-compose-dev.yml up -d