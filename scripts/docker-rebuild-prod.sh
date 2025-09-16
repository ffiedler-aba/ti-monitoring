#!/usr/bin/env bash
set -euo pipefail

GIT_TAG=$(git describe --tags --always 2>/dev/null || echo "")
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "")

docker compose -f docker-compose.yml down && \
  docker compose -f docker-compose.yml build \
    --build-arg TI_VERSION="$GIT_TAG" \
    --build-arg TI_COMMIT="$GIT_SHA" && \
  docker compose -f docker-compose.yml up -d