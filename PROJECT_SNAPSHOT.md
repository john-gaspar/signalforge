# PROJECT_SNAPSHOT

## HEAD
- SHA: b10235bc4b8206f700c8629c87cb1bb4a4262159

## System Summary
SignalForge is a deterministic replay pipeline with FastAPI + RQ worker, producing JSON artifacts per run, guarded by QA gates (benchmark, data quality/drift, graph invariants, load), with docker-compose services (Postgres, Redis, Neo4j) and CI workflows enforcing migrations, gates, and tests.

## Implemented Subsystems
- Replay pipeline — Entry: `app/api/routes_runs.py` (`/runs/replay`); Gate: metrics gate `sentinelqa/gates/gate.py`; Baseline: thresholds.yaml.
- DQ + Drift — Entry: `sentinelqa/dq/run.py`; Gate: same; Baseline: `sentinelqa/baselines/drift_baseline.json`.
- Benchmark — Entry: `sentinelqa/bench/run.py`; Gate: `sentinelqa/gates/bench_gate.py`; Baseline: `sentinelqa/baselines/bench_baseline.json`.
- Graph (Neo4j) — Entry: `sentinelqa/graph/persist.py`; Gate: `sentinelqa/gates/graph_gate.py`; Baseline: none (graph derived).
- Load (Locust) — Entry: `sentinelqa/load/locustfile.py`; Gate: `sentinelqa/gates/load_gate.py`; Baseline: `sentinelqa/baselines/load_baseline.json`.
- CI enforcement — Entry: `.github/workflows/ci.yml` and `.github/workflows/perf.yml`; Gates invoked per workflow stage.

## CI Workflows
- ci.yml — Builds images; starts postgres/redis/neo4j/api/worker; waits for health; seeds run; runs graph gate, benchmark gate, DQ gate, metrics gate, run contract gate; pytest; down services.
- perf.yml — Scheduled/manual only; builds; starts postgres/redis/api/worker; health wait; warmup seed; clears load artifacts; runs Locust headless; generates load report; runs load gate; uploads report; down services.

## Artifact Directories (Runtime Only)
- `artifacts/runs/` — per-run JSON outputs (events, clusters, summary, alert, metrics).
- `artifacts/bench/` — benchmark latest.
- `artifacts/load/` — load-test raw/latest.
- `artifacts/latest_seed_run_id` — last seeded run id.
All `artifacts/*` paths are gitignored (.gitignore line 13).

## Baselines
- `sentinelqa/baselines/drift_baseline.json`
- `sentinelqa/baselines/bench_baseline.json`
- `sentinelqa/baselines/load_baseline.json`

## Canonical Data Boundaries
- Artifacts in `artifacts/runs/` are the canonical domain outputs of the pipeline.
- Postgres stores the same runs/events as authoritative DB state for the API.
- Graph (Neo4j) is derived from artifacts per run via graph gate; not a source of truth.
- Load/bench outputs (`artifacts/bench`, `artifacts/load`) are derived metrics for gates.

## Deterministic Guarantees
- Run Contract gate (`sentinelqa/gates/gate_run_contract.py`) enforces legal run status progression and requires completed runs to include mandatory artifacts and gate outputs (bench report).
- SLO gate (`sentinelqa/gates/gate_slo.py`) enforces run metadata completeness and runtime SLO (default max duration) via `run_metadata.json`.
- Manifest integrity gate (`sentinelqa/gates/gate_manifest_integrity.py`) verifies per-run artifact hashes/bytes/fingerprint against `artifacts/runs/<run_id>/manifest.json` written by the run contract gate.
- Gate ledger + runner (`sentinelqa/gates/runner.py`) executes gates in deterministic order, records provenance to `artifacts/runs/<run_id>/gates.json`, and CI invokes it instead of ad-hoc gate calls.
- Artifact schema gate (`sentinelqa/gates/gate_artifact_schema.py`) validates per-run artifacts against versioned JSON Schemas under `sentinelqa/schemas/`.

## Known Constraints
- perf.yml runs on schedule/manual, not on PR CI.
- CI/gates assume deterministic fixtures (`fixtures/tickets`, `fixtures/golden`).
- No CI business logic in workflows; orchestration only, logic lives under `sentinelqa/`.
- Neo4j is optional at runtime for API/worker; used only by graph gate.
