SignalForge — Codex Operating Instructions

This file defines how Codex must operate in this repository.

It is authoritative.

If this file conflicts with documentation or workflow behavior, this file governs Codex behavior inside the IDE.

⸻

1. Source of Truth Hierarchy

Before making any changes, Codex must read:
	•	PROJECT_SNAPSHOT.md (single-page canonical state)
	•	docs/09_IMPLEMENTATION_STATUS.md (ground truth of what exists)
	•	docs/CURRENT_STATE.md
	•	docs/PROJECT_OPERATING_MODEL.md
	•	README.md

Also scan:
	•	.github/workflows/*
	•	docker-compose.yml
	•	requirements.txt
	•	app/**
	•	sentinelqa/**
	•	tests/**

If documentation and code conflict:
	1.	Code + CI behavior = reality.
	2.	docs/09_IMPLEMENTATION_STATUS.md must be updated to match reality.
	3.	PROJECT_SNAPSHOT.md must reflect actual system state.
	4.	Architecture docs represent target state unless marked implemented.

Documentation must never imply features that do not exist.

⸻

2. Operating Model (Mandatory)

This repository follows strict separation of concerns:
	•	ChatGPT Project UI → produces prompts only.
	•	Codex (VS Code) → executes code changes.

Codex must not invent architecture.
Codex must not operate without reality verification.

⸻

Before Implementing Any Change (Reality Check Required)

Codex must:
	1.	Inspect relevant code paths.
	2.	Inspect CI workflows.
	3.	Inspect environment variable usage.
	4.	Confirm artifact paths.
	5.	Confirm baseline files.
	6.	Confirm database migrations state.
	7.	Confirm gates and entrypoints.

Codex must produce an explicit:

Assumptions vs Reality

List before implementing changes.

If assumptions do not match code, they must be corrected before proceeding.

Codex must refuse to proceed if:
	•	Multiple unrelated goals are requested.
	•	More than one committable chunk is implied.
	•	Secrets are requested to be embedded.
	•	CI behavior would be altered without explicit approval.
	•	Governance files are ignored.

⸻

3. Working Style (Non-Negotiable)

All work must be done in SMALL, committable chunks.

For each chunk:
	1.	State the goal (1–2 lines).
	2.	List exact files to be modified.
	3.	Implement only that scope.
	4.	Verify via:
	•	docker compose (infra-related)
	•	pytest
	•	alembic commands (DB-related)
	•	CI logic (pipeline-related)
	5.	Show git diff --stat.
	6.	Propose a clear commit message.
	7.	STOP and wait for confirmation.

Never:
	•	Mix unrelated refactors.
	•	Rewrite large modules without explicit instruction.
	•	Introduce new architecture without referencing documentation.
	•	Hide logic inside CI workflows.
	•	Expand scope mid-implementation.

⸻

4. CI & Workflow Rules (Strict)

CI YAML must be orchestration-only.

It must NOT contain:
	•	Embedded Python logic
	•	Heredocs
	•	Business logic
	•	Complex shell scripts
	•	Hidden polling loops

All operational logic must live under:

sentinelqa/ci/

Workflows may only:
	•	Build images
	•	Start services
	•	Call repository modules
	•	Run gates
	•	Run tests

Example (allowed):

docker compose run --rm api python -m sentinelqa.ci.seed_run

Example (forbidden):

python - <<'PY'
...
PY

If .github/workflows/*.yml is modified:
	•	actionlint must pass.
	•	Workflow must remain declarative.
	•	Logic must be moved into repository modules.

⸻

5. Determinism Requirements

SignalForge is portfolio-grade infrastructure.

All changes must preserve:
	•	Deterministic replay behavior.
	•	Idempotent persistence.
	•	Stable artifact schemas.
	•	Stable baseline comparisons.
	•	CI reproducibility locally.
	•	No implicit environment coupling.

No timestamps in baselines.
No random IDs in drift checks.
No state accumulation across runs.
No hidden environment magic.

Correctness > cleverness.
Clarity > abstraction.
Determinism > convenience.
Small commits > large rewrites.

⸻

6. Evolution Constraints

SignalForge evolution must deepen architectural rigor, not widen surface area.

Priorities:
	1.	Invariant strengthening
	2.	Deterministic correctness
	3.	Persistence guarantees
	4.	Schema discipline
	5.	Gate enforcement
	6.	CI robustness

Avoid:
	•	Shallow connectors
	•	Superficial integrations
	•	Feature sprawl
	•	External API dependencies unless strategically justified

Architectural depth is preferred over breadth.

⸻

7. Documentation Discipline

When system behavior changes, Codex must update:
	•	docs/09_IMPLEMENTATION_STATUS.md
	•	docs/CURRENT_STATE.md
	•	PROJECT_SNAPSHOT.md

Documentation is considered broken if it drifts from code.

Code + CI override documentation.

A feature is not done until:
	•	Code exists
	•	Tests exist
	•	CI enforces it
	•	Documentation updated
	•	Implementation status updated
	•	No regression risk introduced

⸻

8. Security & Secret Rules

Codex must never:
	•	Hardcode credentials
	•	Commit .env
	•	Embed API keys
	•	Leak tokens into CI
	•	Introduce secrets into repository

Environment variables must be:
	•	Local default-safe
	•	CI-compatible
	•	Explicitly documented

⸻

9. Definition of Done (Per Change)

A change is complete only when:
	•	Code compiles
	•	Tests pass
	•	CI remains green
	•	Gates remain deterministic
	•	Docs updated
	•	Snapshot updated
	•	git diff --stat reviewed
	•	Commit message clear
	•	STOP issued

If any item is missing, the change is incomplete.

⸻

10. Refusal Conditions

Codex must refuse to proceed if:
	•	Prompt attempts multi-phase evolution in one step.
	•	Governance model is bypassed.
	•	CI rules are violated.
	•	Scope creep is introduced.
	•	Documentation update requirement is ignored.

Refusal must explain why and request scope narrowing.

⸻

11. Architectural Boundary

SignalForge canonical boundaries:
	•	Postgres = durable domain state
	•	Neo4j = graph projection layer
	•	Artifacts = deterministic replay snapshots
	•	Baselines = regression contracts
	•	Gates = CI enforcement layer
	•	Workflows = orchestration only

Artifacts are not the primary record.
Derived views must not become source-of-truth.

⸻

This file must be kept aligned with:
	•	PROJECT_SNAPSHOT.md
	•	docs/PROJECT_OPERATING_MODEL.md
	•	docs/09_IMPLEMENTATION_STATUS.md

If architecture evolves, this file must evolve.