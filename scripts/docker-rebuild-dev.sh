#!/usr/bin/env bash
set -euo pipefail

COMPOSE="docker compose -f ./docker-compose-dev.yml"

# Aktiviert TimescaleDB, wenn USE_TSDB=1 gesetzt ist oder --tsdb als Argument übergeben wurde
PROFILE=""
if [[ "${USE_TSDB:-0}" == "1" ]] || [[ "${1:-}" == "--tsdb" ]]; then
  PROFILE="--profile tsdb"
fi

$COMPOSE down
$COMPOSE $PROFILE up --build -d