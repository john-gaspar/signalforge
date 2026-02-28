#!/usr/bin/env bash
set -euo pipefail

python -m compileall sentinelqa app tests

if command -v actionlint >/dev/null 2>&1; then
  actionlint
else
  echo "actionlint not installed; skipping workflow lint"
fi

if command -v ruff >/dev/null 2>&1; then
  ruff .
else
  echo "ruff not installed; skipping lint"
fi
