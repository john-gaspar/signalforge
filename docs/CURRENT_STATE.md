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
- Benchmark gate (`sentinelqa/gates/bench_gate.py`) — **implemented**, enforces pass rate, p95 latency, and F1 thresholds from `sentinelqa/baselines/bench_baseline.json`; will auto-run benchmark if `artifacts/bench/latest.json` is absent and records results to `artifacts/bench/history.jsonl`.
- Trend regression gate (`sentinelqa/gates/gate_trend_regression.py`) — **implemented**, checks linear slopes across recent bench history (F1, pass_rate, p95 latency) with configurable trend thresholds in `sentinelqa/gates/thresholds.yaml`.
- Graph gate (`sentinelqa/gates/graph_gate.py`) — **implemented**, persists stable artifact fields to Neo4j then enforces run/event/cluster edge invariants; waits for Neo4j readiness internally.
- Load gate (`sentinelqa/gates/load_gate.py`) — **implemented**, enforces Locust-based load thresholds using `artifacts/load/latest.json` and baseline `sentinelqa/baselines/load_baseline.json`; only runs in perf workflow/manual.
- Run Contract gate (`sentinelqa/gates/gate_run_contract.py`) — **implemented**, enforces legal run status progression plus required artifacts and bench report presence for completed runs.
- Evidence diff gate (`sentinelqa/gates/gate_evidence_diff.py`) — **implemented**, informational comparison of manifest/schema/bench evidence against baseline bundle `sentinelqa/baselines/evidence/*`, writes `evidence_diff.json` in the run directory.
- Baseline change guard (`sentinelqa/ci/check_baseline_changes.py`) — **implemented**, CI fails if baselines/schemas/contracts change unless `.baseline_update_intent` is modified in the PR (or `BASELINE_UPDATE=1` emergency override).
- CI diagnosis (`sentinelqa/ci/diagnose_ci.py`) — **implemented**, always prints seeded run summary and uploads artifacts/ on CI for debugging.

## CI/CD (see .github/workflows/ci.yml)
1) Baseline guard blocks baseline/schema/contract edits unless `.baseline_update_intent` is modified in the PR (or `BASELINE_UPDATE=1` emergency override)  
2) Build images  
3) Start Postgres/Redis  
4) Run migrations  
5) Start api + worker  
6) Wait for api health (pure-Python, 180s timeout)  
7) Seed run via API (http://api:8000/runs/replay) and record run id  
8) Graph invariants gate (Neo4j)  
9) Benchmark run + gate (golden fixtures vs baseline; generates `artifacts/bench/latest.json` if missing and appends to `artifacts/bench/history.jsonl`)  
10) Trend regression gate (bench history slope checks)  
11) Data Quality gate (includes drift)  
12) Metrics gate  
13) Schema compatibility + artifact schema gates  
14) Evidence diff gate (informational)  
15) CI diagnosis summary (sentinelqa.ci.diagnose_ci)  
16) Run contract + manifest integrity + SLO gates  
17) Pytest  
18) Upload artifacts directory for debugging  
19) Down services  

Manual baseline updates: `update_baselines.yml` workflow_dispatch runs full compose pipeline and calls `python -m sentinelqa.ci.regenerate_baselines --update-bench-baseline`, uploading artifacts for review.  
Actionlint lint job uses docker image `rhysd/actionlint:1.7.0`.

## Performance / Load (separate workflow perf.yml)
- Runs on schedule + manual dispatch, not on PRs.
- Uses Locust headless (defaults: users=5, spawn_rate=1, duration=60s) against `/runs/replay` with fixtures `fixtures/tickets`.
- Generates `artifacts/load/latest.json` and enforces thresholds via load gate; uploads report as artifact. Benchmark results are appended to `artifacts/bench/history.jsonl` for trend regression gate evaluation.

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
- Observability: logging/metrics minimal; tracing absent.

## Developer Notes
- Seed a run: `python -m sentinelqa.ci.seed_run --base-url http://api:8000` (in compose) or `http://localhost:8000` (host). Writes `artifacts/latest_seed_run_id` for gates.
- Run benchmark locally: `python -m sentinelqa.bench.run --base-url http://api:8000 --fixtures fixtures/golden --out artifacts/bench/latest.json` then `python -m sentinelqa.gates.bench_gate`.
- Regenerate drift baseline from a run: `python -m sentinelqa.dq.drift_baseline --run-id <run_id> --force`.
- Run graph gate locally (Neo4j service must be up): `python -m sentinelqa.gates.graph_gate`.
- Run contract gate locally: ensure DB and artifacts exist, then `python -m sentinelqa.gates.gate_run_contract`.
- Run load test locally (compose): bring up services, run `locust -f sentinelqa/load/locustfile.py --headless -u 5 -r 1 -t 60s --host http://api:8000`, then `python -m sentinelqa.load.report --raw artifacts/load/raw.json --out artifacts/load/latest.json` and `python -m sentinelqa.gates.load_gate`.
- `docker compose up -d api worker` is schema-safe because migrations run on startup.
- Health and OpenAPI are stable once the container is up; no uvicorn reload in compose unless `UVICORN_RELOAD=1` is set.
