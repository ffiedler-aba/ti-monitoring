#!/usr/bin/env bash
set -euo pipefail

# Nur git-getrackte Dateien im Repo zählen (keine Pfade außerhalb des Repos)
cd "$(dirname "$0")/.."
cloc --md --vcs=git \
  --match-f='.*\.(py|ya?ml|md|sh|css|js)$' \
  --exclude-ext=hdf5,zip,log,svg,png,jpg,jpeg,gif,ico \
  --out=CLOC_REPORT.md