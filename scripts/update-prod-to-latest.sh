#!/usr/bin/env bash
set -euo pipefail

# This script checks out the latest git tag and rebuilds the production Docker image.

# Resolve repository root based on this script's location
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$REPO_ROOT"

echo "Fetching tags..."
git fetch --tags --force

LATEST_TAG="$(git tag --list | sort -V | tail -n 1)"

if [[ -z "${LATEST_TAG}" ]]; then
  echo "Error: No tags found in repository." >&2
  exit 1
fi

echo "Checking out latest tag: ${LATEST_TAG}"
git checkout --quiet "${LATEST_TAG}"

echo "Running production rebuild script..."
"${REPO_ROOT}/scripts/docker-rebuild-prod.sh"

echo "Done. Currently on tag ${LATEST_TAG}."


