# Current State — SignalForge

Date: February 28, 2026  
Source of truth for implemented vs planned capabilities. See docs/09_IMPLEMENTATION_STATUS.md for canonical checklist.

## Runtime Services
- FastAPI API (`/runs/replay`, `/health`) — **implemented**; `/health` is lightweight and returns 200 when the app is up.
- RQ worker consuming queue `signalforge` — **implemented**.
- Redis + Postgres via docker-compose — **implemented**.
- Startup path runs `alembic upgrade head` in both api and worker containers (see `scripts/start_api.sh`, `scripts/start_worker.sh`); no `create_all` usage.

## Data & Schema
- SQLAlchemy models: Run, Event — **implemented**.
- Alembic migrations — **authoritative**; current head `628737b42193` creates `runs` and `events`.
- Artifacts per run under `artifacts/runs/<run_id>/` — **implemented** (events, clusters, summary, alert, metrics JSON).

## Quality Gates
- Metrics QA gate (`sentinelqa/gates/gate.py`) — **implemented**.
- Data Quality gate (`sentinelqa/dq/run.py`) — **implemented**:
  - Fixture schema validation (Pydantic) for `fixtures/tickets/*`.
  - Artifact structural checks (non-empty events, unique event_id, metrics keys).
  - DB invariant: run exists and succeeded (skips if DB unavailable or not Postgres).

## CI/CD (see .github/workflows/ci.yml)
1) Build images
2) Start Postgres/Redis
3) Run migrations
4) Start api + worker
5) Wait for api health (pure-Python wait, 180s timeout)
6) Seed run via API (http://api:8000/runs/replay)
7) Benchmark run + gate (golden fixtures vs baseline)
8) Data Quality gate
9) Metrics gate
10) Pytest
11) Down services
Actionlint runs in a separate lint job via docker image `rhysd/actionlint:1.7.0`.

## Endpoints
- `/runs/replay` — enqueue deterministic pipeline run; idempotent by config hash.
- `/runs/{run_id}` — retrieve run state/metrics.
- `/health` — readiness/liveness (does not touch DB).

## Testing
- Pytest suite covers API replay, stub stages, migration smoke/drift checks, health endpoint, and startup schema helper.
- Migration tests skip when `DATABASE_URL` is missing or non-Postgres.

## Known Gaps / Planned
- Drift detection (Data Quality) — not implemented.
- Benchmarking gates (golden set, F1/p95 tracking) — not implemented.
- Graph/Neo4j integration — not implemented.
- Load testing scaffold — not implemented.
- Observability: logging/metrics minimal; tracing absent.

## Developer Notes
- Use `python -m sentinelqa.ci.seed_run --base-url http://api:8000` (in compose) or `http://localhost:8000` (host) to seed a run. The wait logic is pure Python and no longer depends on curl.
- Run benchmark locally: `python -m sentinelqa.bench.run --base-url http://api:8000 --fixtures fixtures/golden --out artifacts/bench/latest.json` then `python -m sentinelqa.gates.bench_gate`.
- `docker compose up -d api worker` is schema-safe because migrations run on startup.
- Health and OpenAPI are stable once the container is up; no uvicorn reload in compose unless `UVICORN_RELOAD=1` is set.
