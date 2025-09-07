#!/usr/bin/env bash
set -euo pipefail

# Nur relevante Quellen zählen (per Include-Pattern) und störende Verzeichnisse ausschließen
cloc --md .. \
  --match-f='.*\.(py|ya?ml|md|sh|css|js)$' \
  --not-match-d='(^|/)(\.git|\.venv|data|portable-build|windows-setup-src|build|dist|__pycache__|nginx|letsencrypt-config)(/|$)' \
  --exclude-ext=hdf5,zip,log,svg,png,jpg,jpeg,gif,ico \
  --out=../CLOC_REPORT.md