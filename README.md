# SignalForge — AI Reliability System

## System Architecture

```mermaid
flowchart LR

    subgraph Client
        A[Replay Trigger<br/>POST /runs/replay]
    end

    subgraph API Layer
        B[FastAPI<br/>Run Creation]
    end

    subgraph Queue
        C[RQ Queue<br/>Redis]
    end

    subgraph Worker Layer
        D[Worker<br/>Pipeline Execution]
        E[Artifact Generation]
        F[Metric Collection]
    end

    subgraph Storage
        G[(Postgres<br/>Run State + Metadata)]
        H[(Artifacts Dir<br/>Immutable Outputs)]
    end

    subgraph Reliability Enforcement
        I[SentinelQA<br/>Drift + Budget Checks]
        J[Baseline Store]
    end

    subgraph SLO Domains
        L[Availability]
        M[Performance]
        N[Quality]
        O[Cost]
    end

    subgraph CI
        K[CI Gate<br/>FAIL / WARN / PASS]
    end

    A --> B
    B --> G
    B --> C
    C --> D
    D --> E
    D --> F
    E --> H
    F --> H
    D --> G

    H --> I
    G --> I
    J --> I

    I --> L
    I --> M
    I --> N
    I --> O

    L --> K
    M --> K
    N --> K
    O --> K
```

### Architectural Principles

- API boundary validates and enqueues deterministically  
- Worker executes with explicit state transitions  
- Artifacts are immutable once written  
- SentinelQA enforces baseline-controlled regression  
- CI blocks FAIL-level reliability violations  

---

## What it is / What it proves
SignalForge is a deterministic replay harness for reliability enforcement. It proves:
- Replays are reproducible: artifacts and manifest fingerprints remain stable across runs.
- Domain quality gates block regressions (metrics, DQ + drift, benchmark, graph, schema, contract).
- CI enforces the entire gate ledger end-to-end, with optional chaos and replay checks.

---

## Quick start (docker-compose, CI-parity helpers)
1) Write env (defaults are compose-safe):
```bash
python -m sentinelqa.ci.write_env --path .env
```
2) Bring up dependencies and apply migrations:
```bash
docker compose up -d postgres redis neo4j
docker compose run --rm api alembic upgrade head
```
3) Start services:
```bash
docker compose up -d api worker
```
4) Seed a deterministic run (writes `artifacts/latest_seed_run_id`):
```bash
docker compose run --rm api python -m sentinelqa.ci.seed_run --base-url http://api:8000
```
5) Run gates locally (pick what you need):
```bash
# Graph gate (needs neo4j up)
docker compose run --rm api python -m sentinelqa.gates.graph_gate
# Benchmark gate
docker compose run --rm api python -m sentinelqa.gates.bench_gate
# Data Quality + drift
docker compose run --rm api python -m sentinelqa.dq.run
# Metrics QA gate
docker compose run --rm api python sentinelqa/gates/gate.py
# Contract + manifest integrity + SLO are executed via the runner:
docker compose run --rm api python -m sentinelqa.gates.runner
```
6) Inspect artifacts:
```
artifacts/runs/<run_id>/
```
Neo4j is gate-only; API/worker do not depend on it at runtime.

---

## Reliability Gates (what they enforce / how to run)
- Metrics gate: latency/alerts thresholds from `sentinelqa/gates/thresholds.yaml`.  
  Run: `docker compose run --rm api python sentinelqa/gates/gate.py`
- Data Quality + Drift: schema + structural checks, drift vs `sentinelqa/baselines/drift_baseline.json`.  
  Run: `docker compose run --rm api python -m sentinelqa.dq.run`
- Benchmark gate: accuracy/latency vs `sentinelqa/baselines/bench_baseline.json`.  
  Run: `docker compose run --rm api python -m sentinelqa.gates.bench_gate`
- Graph gate: Neo4j projection + invariants.  
  Run: `docker compose run --rm api python -m sentinelqa.gates.graph_gate`
- Artifact schema gate: validates run artifacts against schemas in `sentinelqa/schemas/`.  
  Run: `docker compose run --rm api python -m sentinelqa.gates.gate_artifact_schema`
- Schema compatibility gate: blocks breaking schema changes vs `sentinelqa/schemas_baseline/v1/`.  
  Run: `docker compose run --rm api python -m sentinelqa.gates.gate_schema_compat`
- Contract index gate: enforces canonical contract (gate order, required artifacts, schemas).  
  Run: `docker compose run --rm api python -m sentinelqa.gates.gate_contract_index`
- Run contract gate: legal status transitions, required artifacts, bench report.  
  Run: `docker compose run --rm api python -m sentinelqa.gates.gate_run_contract`
- Manifest integrity gate: hashes/sizes/fingerprint for artifacts.  
  Run: `docker compose run --rm api python -m sentinelqa.gates.gate_manifest_integrity`
- SLO gate: run metadata completeness + runtime SLO.  
  Run: `docker compose run --rm api python -m sentinelqa.gates.gate_slo`
- Optional realism gates (env controlled):  
  - Failure injection (`FAILURE_INJECTION=1`)  
  - Deterministic replay (`DETERMINISTIC_REPLAY=1`)  
  Run via runner with env set: `FAILURE_INJECTION=1 DETERMINISTIC_REPLAY=1 docker compose run --rm api python -m sentinelqa.gates.runner`
- Perf/load gate (perf workflow only): `docker compose run --rm api python -m sentinelqa.gates.load_gate` after generating load report.

---

## CI Workflows
- `ci.yml`: build images → start postgres/redis/neo4j/api/worker → migrations → seed run → gate runner (ledgered gates) → pytest → compose down. Snapshot SHA check runs up front; graph preflight (static/runtime) runs before gates.
- `perf.yml`: scheduled/manual load test; builds → starts postgres/redis/api/worker → health wait → warmup seed → run Locust → generate load report → load gate → upload artifacts → down.
- `full_validation.yml`: scheduled/manual; builds → starts full stack → seed run → gate runner with optional realism gates enabled (failure injection, deterministic replay) → upload `artifacts/**` for debugging → down.

---

## Runtime boundaries
- Neo4j is used only by the graph gate; API/worker runtime does not depend on Neo4j.
- Artifacts under `artifacts/runs/<run_id>/` are the canonical outputs; Postgres mirrors run state; manifests record fingerprints for determinism.

## Migrations (Alembic)
- Upgrade to latest: `docker compose run --rm api alembic upgrade head`
- Create revision (autogenerate): `docker compose run --rm api alembic revision --autogenerate -m "..."`
 - Note: api/worker containers run `alembic upgrade head` on startup for convenience.

## Data Quality Gate
- Run locally: `python -m sentinelqa.dq.run`

## Benchmark Gate
- Run benchmark: `python -m sentinelqa.bench.run --base-url http://api:8000 --fixtures fixtures/golden --out artifacts/bench/latest.json`
- Check against baseline: `python -m sentinelqa.gates.bench_gate`
- Accuracy is computed via expected event_ids in `fixtures/golden/expectations.json`; baseline requires F1 to stay above `min_f1` (see `sentinelqa/baselines/bench_baseline.json`).

## Preflight
- `./scripts/preflight.sh` (compileall + optional actionlint/ruff)
- Graph MVP preflight (Neo4j readiness + idempotency): `docker compose up -d postgres redis neo4j api worker && docker compose run --rm api python -m sentinelqa.ci.graph_preflight --mode runtime`
- Perf (Locust): `docker compose up -d postgres redis api worker && docker compose run --rm api locust -f sentinelqa/load/locustfile.py --headless -u 5 -r 1 -t 60s --host http://api:8000 && docker compose run --rm api python -m sentinelqa.load.report --raw artifacts/load/raw.json --out artifacts/load/latest.json && docker compose run --rm api python -m sentinelqa.gates.load_gate`

## Environment variables
- `DATABASE_URL` (e.g., `postgresql+psycopg://signalforge:signalforge@postgres:5432/signalforge`)
- `REDIS_URL` (e.g., `redis://redis:6379/0`)
- `ARTIFACTS_DIR` (default `/code/artifacts` in Docker, `./artifacts` locally; optional in CI helper)
- `RQ_QUEUE_NAME` (default `signalforge`)

## QA thresholds
Defined in `sentinelqa/gates/thresholds.yaml` (e.g., latency max, alerts_sent min).

## Notes
- Idempotent run creation: same config => same `run_id`.
- Pipeline writes artifacts and metrics under `artifacts/runs/<run_id>/`.
- Stubs: stages are deterministic placeholders; replace with real logic as needed.

## Portfolio story (shift-left QA)
- Purpose: demonstrate building a quality harness in parallel with feature dev—fixtures, deterministic pipeline, metrics-based gate, and CI wiring that will later wrap real APIs and ML/HF models.
- What’s here: replay endpoint using fixture tickets, stub stages, artifact/metrics generation, QA gate enforced in CI, placeholder pytest scaffold.
- How to evolve: swap stub stages for real integrations (APIs, Hugging Face models), add more fixtures (anonymized/captured), broaden thresholds, and grow pytest suites (unit, integration, e2e).
- CI contract: seed run → QA gate → pytest. This stays stable as logic becomes “real,” keeping regressions visible early.
- Workflow: solo is fine to commit to `main`; if collaborators join, use short-lived branches/PRs so QA gate and tests run on every change.

## Development Model
This project uses a strict ChatGPT (prompt generation) + Codex (implementation) workflow. See docs/PROJECT_OPERATING_MODEL.md and AGENT.md.
