#!/usr/bin/env bash
set -euo pipefail

python -m sentinelqa.ci.startup --db-url "${DATABASE_URL:?DATABASE_URL required}" --wait-timeout 60
if [ "${UVICORN_RELOAD:-0}" = "1" ]; then
  exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
else
  exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000
fi
