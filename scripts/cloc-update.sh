#!/usr/bin/env bash
set -euo pipefail

# Nur relevante Quellverzeichnisse zählen
# Root-Struktur: app + pages + scripts + docs + assets + Docker/Compose
cloc --md .. \
  --include-dir=assets,pages,scripts,docs \
  --match-f="\\.(py|yml|yaml|md|sh|css|js)$" \
  --exclude-dir=.git,.venv,data,portable-build,windows-setup-src,build,dist,__pycache__,nginx,letsencrypt-config \
  --exclude-ext=hdf5,zip,log,svg,png,jpg,jpeg,gif,ico \
  --out=../CLOC_REPORT.md