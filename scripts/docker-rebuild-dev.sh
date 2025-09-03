#!/usr/bin/env bash
set -euo pipefail

COMPOSE="docker compose -f ./docker-compose-dev.yml"

# TimescaleDB ist immer aktiviert (Standard-Datenbank)
$COMPOSE down
$COMPOSE up --build -d