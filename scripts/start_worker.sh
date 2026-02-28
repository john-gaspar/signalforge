#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
import os
from urllib.parse import urlparse
from sentinelqa.ci.startup import wait_for_host, has_alembic_table, ensure_schema

db_url = os.environ["DATABASE_URL"]
parsed = urlparse(db_url)
host = parsed.hostname or "localhost"
port = parsed.port or 5432

wait_for_host(host, port, timeout=60, interval=1.0)

if not has_alembic_table(db_url):
    ensure_schema(db_url, wait_timeout=60)
PY

exec rq worker "${RQ_QUEUE_NAME:-signalforge}" --with-scheduler
