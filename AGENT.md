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

If documentation and code conflict:

- `docs/09_IMPLEMENTATION_STATUS.md` = ground truth of what exists.
- Architecture docs = target state unless marked implemented.

---

# 2. Working Style (Mandatory)

All work must be done in SMALL, committable chunks.

For each chunk:

1. State the goal (1–2 lines).
2. List exact files to be modified.
3. Implement only that scope.
4. Verify via:
   - docker compose (infra-related)
   - pytest
   - alembic commands (DB-related)
   - CI logic (pipeline-related)
5. Show `git diff --stat`.
6. Propose a clear commit message.
7. STOP and wait for confirmation.

Never:

- Mix unrelated refactors.
- Rewrite large modules unless explicitly instructed.
- Introduce new architecture without referencing docs.
- Hide logic inside CI workflows.

---

# Operating Model (Mandatory)

This repository follows a strict separation of concerns:

- ChatGPT Project UI → produces prompts only.
- Codex (VS Code) → executes and modifies repository code.

This separation is structural and non-negotiable.

Codex must never assume conversational memory as source of truth.
All decisions must be grounded in repository state.

---

## Snapshot Anchor Requirement

Before implementing any change, Codex must assume the repository HEAD commit is the only valid state reference.

All reasoning must be based on:

- Current HEAD SHA
- Current working tree state
- Actual code in repository
- Active CI workflows

Never rely on historical conversation context.

---

## Mandatory Reality Check (Pre-Implementation)

Before writing or modifying any code, Codex must:

1. Inspect relevant code paths.
2. Inspect relevant CI workflows under `.github/workflows/`.
3. Inspect environment variable usage (`os.getenv`, settings modules, docker-compose).
4. Confirm artifact directories and baseline paths.
5. Confirm migration state if DB-related.
6. Confirm tests covering the affected area.

Codex must produce an explicit:

"Assumptions vs Reality" list

Each assumption must be confirmed with:
- File path
- Relevant line reference OR command evidence

If documentation conflicts with code:
- Code + workflows override documentation.
- Documentation must be updated in the same commit.

---

## Scope Control Rules

For every task:

Codex must explicitly confirm:

- One committable chunk only.
- No unrelated refactors.
- No hidden behavior changes.
- No secrets, credentials, or tokens introduced into code or workflows.
- No inline CI business logic introduced.

If the requested change implies multiple subsystems, Codex must:
- Decompose the task.
- Implement only the smallest safe unit.
- STOP.

---

## Required Output (Post-Implementation)

After completing a change, Codex must output:

1. Files changed (exact list).
2. Commands executed + results.
3. Verification steps performed.
4. `git diff --stat`.
5. Proposed commit message.
6. STOP.

No additional speculative suggestions.

---

## Documentation Discipline (Non-Negotiable)

Whenever system behavior changes, Codex must update:

- docs/09_IMPLEMENTATION_STATUS.md
- docs/CURRENT_STATE.md
- PROJECT_SNAPSHOT.md

If documentation is not updated, the feature is incomplete.

Documentation is considered invalid if it drifts from code.

CI workflows and repository code are authoritative over docs.

---

# 3. CI & Workflow Rules (Non-Negotiable)

CI YAML must be declarative orchestration only.

It must NOT contain:

- Multi-line Python scripts
- Heredocs
- Embedded business logic
- Non-trivial shell logic
- Complex polling loops

All operational logic must live in repository modules under:

sentinelqa/ci/

Workflows may only:

- Build images
- Start services
- Call repo modules
- Run gates
- Run tests

Example:

docker compose run –rm api python -m sentinelqa.ci.seed_run

NOT:

python - <<‘PY’
…
PY

If `.github/workflows/*.yml` is modified:

- actionlint must pass.
- Workflow must remain orchestration-only.
- Logic must be moved into modules.

---

# 4. Preflight & Regression Prevention

Any structural change must reduce future fragility.

Required safeguards:

- Workflow YAML must be linted (actionlint in CI).
- Python syntax must compile (`python -m compileall`).
- Deterministic seed logic must be testable outside CI.
- No hidden environment coupling.

When introducing CI logic:

- It must be executable locally via docker compose.
- It must not depend on runner-specific quirks.
- It must fail loudly and clearly.

If a CI failure occurs:

- Root cause must be eliminated structurally.
- A guardrail must be added to prevent recurrence.
- Documentation must be updated if necessary.

---

# 5. Execution Order

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

Do not jump phases without explicit instruction.

---

# 6. Quality Bar

Every new feature must:

- Be deterministic where possible.
- Be testable.
- Integrate into CI.
- Update `docs/09_IMPLEMENTATION_STATUS.md`.
- Not degrade existing guarantees.

If something is implemented, mark it.
If not implemented, do not imply it exists.

---

# 7. Robustness Principles

SignalForge is portfolio-grade infrastructure.

Therefore:

- CI must be reproducible locally.
- Schema changes must be migration-driven.
- Quality gates must be enforceable.
- No implicit state.
- No environment magic.
- No fragile YAML tricks.

Correctness > cleverness.  
Clarity > abstraction.  
Determinism > convenience.  
Small commits > big rewrites.

---

# 8. Definition of Done (Per Feature)

A feature is complete only when:

- Code exists
- Tests exist
- CI enforces it
- Documentation updated
- Implementation status updated
- No inline CI logic introduced
- No regression risk introduced

If any of these are missing, it is not done.

# Documentation

Error budget policy (docs/ERROR_BUDGET_POLICY.md) — ✅ Documented  
Run lifecycle state machine (docs/RUN_STATE_MACHINE.md) — ✅ Documented  

This file must be updated whenever a planned item becomes implemented.