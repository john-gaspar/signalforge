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

## Overview

SignalForge is a reliability-first AI system designed to enforce:

- Baseline-controlled regression
- Deterministic replay
- Error-budget governance
- Explicit lifecycle semantics
- CI-enforced reliability guarantees

This repository demonstrates ownership of AI system reliability — not just automation.

The focus is operational discipline across:

- Schema integrity
- Structural invariants
- Drift detection
- Latency regression
- Cost control
- Failure isolation

---

## Quick start
1. Copy env: `cp .env.example .env` and fill values.
2. Start backing services: `docker compose up -d postgres redis`.
3. Run DB migrations (once): `docker compose run --rm api alembic upgrade head`.
4. Run API + worker (separate terminals):
   - API: `docker compose up api`
   - Worker: `docker compose up worker`
   (containers auto-run `alembic upgrade head` on startup)
5. Add fixtures in `fixtures/tickets/*.json`.
6. Trigger a replay run:
   ```bash
   curl -X POST http://localhost:8000/runs/replay \
     -H "Content-Type: application/json" \
     -d '{"fixtures_dir":"fixtures/tickets","fault_config":{}}'
   ```
7. Check status: `curl http://localhost:8000/runs/<run_id>`.
8. Inspect artifacts: `artifacts/runs/<run_id>/`.
9. QA gate (local venv): `python3 sentinelqa/gates/gate.py`.
   - Containerized gate (CI parity): `docker compose run --rm api python sentinelqa/gates/gate.py`.
10. Data Quality gate: `python -m sentinelqa.dq.run`

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

## Environment variables
- `DATABASE_URL` (e.g., `postgresql+psycopg://signalforge:signalforge@postgres:5432/signalforge`)
- `REDIS_URL` (e.g., `redis://redis:6379/0`)
- `ARTIFACTS_DIR` (default `/code/artifacts` in Docker, `./artifacts` locally)
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
