#!/usr/bin/env bash
set -euo pipefail

cd /root/ti-monitoring
git pull

COMPOSE="docker compose -f docker-compose.yml"

# TimescaleDB ist immer aktiviert (Standard-Datenbank)
$COMPOSE down
$COMPOSE up --build -d