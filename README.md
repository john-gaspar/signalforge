# SignalForge — AI Reliability System

[![CI](https://github.com/john-gaspar/signalforge/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/john-gaspar/signalforge/actions/workflows/ci.yml) [![Perf](https://github.com/john-gaspar/signalforge/actions/workflows/perf.yml/badge.svg?branch=main)](https://github.com/john-gaspar/signalforge/actions/workflows/perf.yml)

## What this proves
- Deterministic replay pipeline
- Artifact contract enforcement (schema gate)
- Baseline-controlled drift detection
- CI-enforced reliability gates (graph, bench, DQ, metrics)
- Scheduled performance enforcement

## Architecture

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

## CI pipeline

```mermaid
flowchart LR
  checkout[Checkout + snapshot guard] --> env[Write .env - sentinelqa.ci.write_env]
  env --> build[Build images]
  build --> start[Start postgres/redis/neo4j]
  start --> waitpg[Wait TCP postgres:5432]
  waitpg --> migrate[Alembic upgrade head]
  migrate --> services[Start api + worker]
  services --> health[Wait api health - sentinelqa.ci.wait_http]
  health --> seed[Seed run via API]
  seed --> gpstatic[Graph preflight - static]
  gpstatic --> gpruntime[Graph preflight - runtime]
  gpruntime --> gates[Gate runner - graph -> bench -> dq -> qa -> schema -> metrics]
  gates --> pytest[Pytest]
  pytest --> down[Compose down]
```

## Gates matrix

| Gate | What it enforces | Where it runs | Command | Typical failure meaning |
| --- | --- | --- | --- | --- |
| Graph invariants | Neo4j projection completeness + edge rules | CI (runner), Local | `docker compose run --rm api python -m sentinelqa.gates.graph_gate` | Missing nodes/edges or idempotency break |
| Benchmark | Pass rate, p95 latency, F1 vs `bench_baseline.json` | CI (runner), Local | `docker compose run --rm api python -m sentinelqa.gates.bench_gate` | Regression vs benchmark baseline |
| Data Quality + Drift | Fixture/schema validity, drift vs `drift_baseline.json` | CI (runner), Local | `docker compose run --rm api python -m sentinelqa.dq.run` | Drift or invalid artifacts |
| Metrics QA | Latency/alerts thresholds | CI (runner), Local | `docker compose run --rm api python sentinelqa/gates/gate.py` | Metrics below thresholds |
| Schema compatibility | Backward compatibility vs `schemas_baseline/v1` | CI (runner), Local | `docker compose run --rm api python -m sentinelqa.gates.gate_schema_compat` | Breaking schema change |
| Artifact schema | JSON schema validity for artifacts | CI (runner), Local | `docker compose run --rm api python -m sentinelqa.gates.gate_artifact_schema` | Artifact shape mismatch |
| Failure injection | Tamper/fault detection (optional env gate) | CI (runner) | `docker compose run --rm api python -m sentinelqa.gates.gate_failure_injection` | Tamper not detected |
| Deterministic replay | Fingerprint equality across replays | CI (runner) | `docker compose run --rm api python -m sentinelqa.gates.gate_deterministic_replay` | Non-deterministic artifacts |
| Run contract | Run lifecycle + required artifacts | CI (runner), Local | `docker compose run --rm api python -m sentinelqa.gates.gate_run_contract` | Missing artifacts or illegal status path |
| Manifest integrity | Hashes + fingerprint of artifacts | CI (runner), Local | `docker compose run --rm api python -m sentinelqa.gates.gate_manifest_integrity` | Manifest/file hash mismatch |
| SLO | Run metadata completeness + duration budget | CI (runner), Local | `docker compose run --rm api python -m sentinelqa.gates.gate_slo` | SLO/metadata missing |

## Determinism & baselines
- Artifacts live under `artifacts/runs/<run_id>/`; manifest.json captures per-file hashes and a fingerprint for determinism.
- Baselines: `sentinelqa/baselines/bench_baseline.json`, `sentinelqa/baselines/drift_baseline.json`, `sentinelqa/baselines/load_baseline.json` (perf). Thresholds/tolerances are explicit; changes must be intentional.
- Gate runner (`python -m sentinelqa.gates.runner`) executes the ledgered gate order and writes `gates.json` alongside artifacts for auditability.

## Deterministic fingerprint example

Commands (local CI-parity):
```bash
docker compose build
docker compose up -d postgres redis neo4j
docker compose run --rm api alembic upgrade head
docker compose up -d api worker
docker compose run --rm api python -m sentinelqa.ci.seed_run --base-url http://api:8000
python -m sentinelqa.cli.diagnose --run-id 80294c1eaa340d4262d8e8ddd3c57879 --artifacts-dir artifacts
```

Sample output (real run):
```
Run: 80294c1eaa340d4262d8e8ddd3c57879
Manifest: fingerprint=b24a7d79c19a1d4dec5db20b2b7f3ea206ef9ae265bc3b07034eeefa11c48e0b files=5
Evidence files:
- artifacts/runs/80294c1eaa340d4262d8e8ddd3c57879/manifest.json
```

## Security Notes
- .env is never committed; it is generated via `python -m sentinelqa.ci.write_env --path .env`.
- docker-compose uses dev-only default credentials; override via environment for CI/production.
- Artifacts directory (`artifacts/**`) is gitignored; only baselines and schemas are tracked.
- Secrets stay in env/CI secrets; repository contains no embedded keys.
