# Architecture — Current vs Target State

This document separates what is implemented today from the intended target state.

---

# 1️⃣ Current State (As Implemented)

SignalForge currently operates as:

Client / CI
    ↓
FastAPI (/runs/replay)
    ↓
Postgres (Run metadata only)
    ↓
Redis (RQ enqueue)
    ↓
Worker (process_run)
    ↓
Pipeline (stub stages)
    ↓
Filesystem artifacts (JSON)
    ↓
SentinelQA metrics gate
    ↓
CI pass/fail

### Storage

Postgres:
- `runs` table
- `events` table (currently unused in pipeline)

Filesystem:
- artifacts/runs/<run_id>/
  - events.json
  - clusters.json
  - summary.json
  - alert.json
  - metrics.json

There is currently:
- No graph DB
- No vector DB
- No ingestion connectors
- No object storage
- No ML models (stub logic only)

This is intentional: the system is currently a deterministic replay + evaluation harness.

---

# 2️⃣ Immediate Next Step (Before Expanding Architecture)

Alembic migrations will become the authoritative schema manager.

Flow after Alembic integration:

Services up
    ↓
alembic upgrade head
    ↓
Seed run
    ↓
QA gate
    ↓
pytest

`Base.metadata.create_all()` will be removed or guarded.

---

# 3️⃣ Target Architecture (Post-Weekend Evolution)

Client / CI
    ↓
FastAPI (/runs/replay)
    ↓
Postgres (Run + canonical domain state)
    ↓
Redis queue
    ↓
Worker
    ↓
Pipeline stages
    ↓
Artifacts (immutable JSON snapshots)
    ↓
Graph persistence (Neo4j — planned)
    ↓
Data Quality Gate
    ↓
Benchmark Gate
    ↓
Load/Performance validation
    ↓
CI pass/fail

---

# 4️⃣ Planned Storage Layers

Postgres
- Run
- Event (canonical)
- Cluster
- Alert
- Idempotency keys

Graph DB (Planned)
- Run → Event → Cluster → Alert lineage

Vector DB (Future)
- Embeddings for clustering

Object Storage (Future)
- Raw audio
- Transcript artifacts
- Model outputs

---

# Architectural Principle

Artifacts are immutable.
Databases are query layers.
CI gates enforce correctness and regression control.