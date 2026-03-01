# Current State — SignalForge

Date: March 1, 2026  
Single-page snapshot for external LLM agents. For the canonical checklist see docs/09_IMPLEMENTATION_STATUS.md.

## Runtime Services
- FastAPI API (`/runs/replay`, `/health`) — **implemented**; `/health` is lightweight and DB-independent.
- RQ worker consuming queue `signalforge` — **implemented**.
- Redis + Postgres via docker-compose — **implemented**.
- Neo4j (local-only, compose service `neo4j` with auth neo4j/signalforge) — **implemented** for gates; API/worker do not depend on it at runtime.
- Startup path runs `alembic upgrade head` in api/worker entrypoints (see `scripts/start_api.sh`, `scripts/start_worker.sh`); no `create_all` usage.

## Data & Schema
- SQLAlchemy models: Run, Event — **implemented**.
- Alembic migrations — **authoritative**; current head `628737b42193` creates `runs` and `events`.
- Artifacts per run under `artifacts/runs/<run_id>/` — **implemented** (events, clusters, summary, alert, metrics JSON). Latest seed run id is written to `artifacts/latest_seed_run_id` by the CI/local seeder.

## Quality Gates
- Metrics QA gate (`sentinelqa/gates/gate.py`) — **implemented**.
- Data Quality gate (`sentinelqa/dq/run.py`) — **implemented**:
  - Fixture schema validation (Pydantic) for `fixtures/tickets/*`.
  - Artifact structural checks (non-empty events, unique event_id, metrics keys).
  - DB invariant: run exists and succeeded (skips if DB unavailable or not Postgres).
  - Drift detection: compares artifact-derived summaries to baseline (`sentinelqa/baselines/drift_baseline.json`) with numeric/distribution tolerances; default warn locally, fail in CI. Uses `artifacts/latest_seed_run_id` if present, else latest run directory.
- Benchmark gate (`sentinelqa/gates/bench_gate.py`) — **implemented**, enforces pass rate, p95 latency, and F1 thresholds from `sentinelqa/baselines/bench_baseline.json`; will auto-run benchmark if `artifacts/bench/latest.json` is absent.
- Graph gate (`sentinelqa/gates/graph_gate.py`) — **implemented**, persists stable artifact fields to Neo4j then enforces run/event/cluster edge invariants; waits for Neo4j readiness internally.
- Load gate (`sentinelqa/gates/load_gate.py`) — **implemented**, enforces Locust-based load thresholds using `artifacts/load/latest.json` and baseline `sentinelqa/baselines/load_baseline.json`; only runs in perf workflow/manual.

## CI/CD (see .github/workflows/ci.yml)
1) Build images  
2) Start Postgres/Redis  
3) Run migrations  
4) Start api + worker  
5) Wait for api health (pure-Python, 180s timeout)  
6) Seed run via API (http://api:8000/runs/replay) and record run id  
7) Graph invariants gate (Neo4j)  
8) Benchmark run + gate (golden fixtures vs baseline; generates `artifacts/bench/latest.json` if missing)  
9) Data Quality gate (includes drift)  
10) Metrics gate  
11) Pytest  
12) Down services  
Actionlint lint job uses docker image `rhysd/actionlint:1.7.0`.

## Performance / Load (separate workflow perf.yml)
- Runs on schedule + manual dispatch, not on PRs.
- Uses Locust headless (defaults: users=5, spawn_rate=1, duration=60s) against `/runs/replay` with fixtures `fixtures/tickets`.
- Generates `artifacts/load/latest.json` and enforces thresholds via load gate; uploads report as artifact.

## Endpoints
- `/runs/replay` — enqueue deterministic pipeline run; idempotent by config hash.
- `/runs/{run_id}` — retrieve run state/metrics.
- `/health` — readiness/liveness (does not touch DB).
- Benchmark accuracy — event-level precision/recall/F1 vs expected event_ids in `fixtures/golden/expectations.json`; enforced via benchmark gate baseline.
- Graph: nodes/edges are derived from artifacts via graph gate; API/worker do not depend on Neo4j.

## Testing
- Pytest suite covers API replay, stub stages, benchmark scoring/gate, drift comparison, migration smoke/drift checks, health endpoint, and startup schema helper.
- Migration tests skip when `DATABASE_URL` is missing or non-Postgres.

## Known Gaps / Planned
- Graph/Neo4j integration — not implemented.
- Load testing scaffold — not implemented.
- Observability: logging/metrics minimal; tracing absent.

## Developer Notes
- Seed a run: `python -m sentinelqa.ci.seed_run --base-url http://api:8000` (in compose) or `http://localhost:8000` (host). Writes `artifacts/latest_seed_run_id` for gates.
- Run benchmark locally: `python -m sentinelqa.bench.run --base-url http://api:8000 --fixtures fixtures/golden --out artifacts/bench/latest.json` then `python -m sentinelqa.gates.bench_gate`.
- Regenerate drift baseline from a run: `python -m sentinelqa.dq.drift_baseline --run-id <run_id> --force`.
- Run graph gate locally (Neo4j service must be up): `python -m sentinelqa.gates.graph_gate`.
- Run load test locally (compose): bring up services, run `locust -f sentinelqa/load/locustfile.py --headless -u 5 -r 1 -t 60s --host http://api:8000`, then `python -m sentinelqa.load.report --raw artifacts/load/raw.json --out artifacts/load/latest.json` and `python -m sentinelqa.gates.load_gate`.
- `docker compose up -d api worker` is schema-safe because migrations run on startup.
- Health and OpenAPI are stable once the container is up; no uvicorn reload in compose unless `UVICORN_RELOAD=1` is set.
