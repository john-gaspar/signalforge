# SignalForge — Codex Operating Instructions

This file defines how Codex must operate in this repository.

It is authoritative.

---

# 1. Source of Truth

Before making changes, always read:

- docs/00_PROJECT_VISION.md
- docs/01_ARCHITECTURE_TARGET_STATE.md
- docs/02_GRAPH_DATABASE_PLAN.md
- docs/03_DATA_QUALITY_STRATEGY.md
- docs/04_ML_BENCHMARKING_PLAN.md
- docs/05_LOAD_TESTING_PLAN.md
- docs/06_CI_EVOLUTION.md
- docs/07_DEBUGGING_AND_SYSTEM_VALIDATION.md
- docs/08_SKILL_ALIGNMENT_MAP.md
- docs/09_IMPLEMENTATION_STATUS.md

Also scan:
- README.md
- docker-compose.yml
- .github/workflows/ci.yml
- requirements.txt
- app/**
- sentinelqa/**
- tests/**

If documentation and code conflict, treat:
- docs/09_IMPLEMENTATION_STATUS.md as the ground truth for what is implemented.
- Architecture docs as target state unless explicitly marked implemented.

---

# 2. Working Style (Mandatory)

All work must be done in SMALL, committable chunks.

For each chunk:

1. State the goal (1–2 lines).
2. List exact files to be modified.
3. Implement only that scope.
4. Verify via:
   - docker compose (if infra-related)
   - pytest
   - alembic commands (if DB-related)
   - CI workflow logic (if pipeline-related)
5. Show `git diff --stat`.
6. Propose a clear commit message.
7. STOP and wait for confirmation.

Never:
- Mix unrelated refactors.
- Rewrite large modules unless explicitly instructed.
- Introduce new architecture without referencing docs.

---

# 3. Execution Order

Strict order of evolution:

Phase A — Schema Stability
A1) Add Alembic scaffold
A2) Create initial migration
A3) Remove/guard create_all
A4) Wire migrations into CI
A5) Add migration smoke test

Phase B — Quality & Graph
B1) Data Quality gate
B2) Benchmark gate
B3) Graph DB integration
B4) Load testing scaffold

Do not jump ahead without completing earlier phases.

---

# 4. Quality Bar

Every new feature must:
- Be testable
- Be deterministic where possible
- Integrate into CI
- Update docs/09_IMPLEMENTATION_STATUS.md

If something is implemented, mark it.
If not implemented, do not imply it exists.

---

# 5. System Philosophy

SignalForge is:

- A deterministic replay + evaluation harness evolving into
- A graph-backed, ML-evaluated incident radar
- With automated quality enforcement
- And production-grade schema management

Correctness > cleverness.
Clarity > abstraction.
Small commits > big rewrites.

---

# 6. Definition of Done (Per Feature)

A feature is complete when:

- Code exists
- Tests exist
- CI enforces it
- Documentation updated
- Implementation status updated

If any of these are missing, it is not done.