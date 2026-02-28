# Debugging & System Validation Guide

## Objective

Improve Linux and system-level debugging capability.

---

## Core Commands

docker compose logs -f
docker compose ps
docker compose exec api bash
tail -f artifacts/runs/<id>/metrics.json
grep ERROR logs
top
htop
ps aux
lsof -i
ss -lnt

---

## Debug Workflow

1. Reproduce failure locally
2. Inspect worker logs
3. Inspect artifacts
4. Verify DB row state
5. Verify graph state
6. Compare against baseline metrics

---

## Interview Framing

"I debug across layers:
API → Queue → Worker → DB → Graph → Artifacts.
I isolate failure domains systematically."

---

## Run Failure Triage Flow

When a run fails, debugging must follow the deterministic lifecycle defined in `RUN_STATE_MACHINE.md`.

Failure triage is performed in layers:

### 1️⃣ Identify Terminal State

Check run state:

- COMPLETED → Not a failure
- FAILED → Terminal failure
- RETRYING → Transient failure in progress
- RUNNING stuck → Potential worker or queue issue

Inspect:

- Run row in DB (state + failure_reason)
- Retry count
- Timestamps (state transition history)

---

### 2️⃣ Categorize Failure Type

Failures fall into one of four categories:

**Execution Failures**
- Worker exception
- Timeout
- Retry limit exceeded
- Queue failure

**Structural Failures**
- Invariant violation
- Artifact mismatch
- Missing expected entities

**Drift / Quality Failures**
- Accuracy regression
- Label distribution divergence
- Drift threshold exceeded

**Budget Violations**
- Latency regression
- Cost regression
- Error rate above SLO

The failure_reason field must explicitly indicate which category triggered failure.

---

### 3️⃣ Inspect Logs

Use:

docker compose logs -f  
docker compose logs worker  
docker compose logs api  

Look for:

- Correlation ID
- run_id
- state transition logs
- Exception traces
- Drift or budget violation messages

Structured logs should include:

- run_id
- previous_state
- new_state
- model_id
- dataset_version

---

### 4️⃣ Inspect Metrics & Artifacts

Check:

- artifacts/runs/<id>/metrics.json
- Drift comparison report
- Latency histogram
- Cost summary

Compare against baseline:

- Same run_config_hash
- Same dataset_version

If configuration differs, comparison is invalid.

---

### 5️⃣ Verify Data Layer

Confirm:

- Artifacts persisted correctly
- No partial writes
- No duplicate artifacts
- DB state consistent with run lifecycle

Check:

- alembic_version table exists
- No migration mismatch
- Worker did not bypass invariant enforcement

---

### 6️⃣ Determine Corrective Action

- Structural issue → Fix pipeline logic
- Drift regression → Investigate model/prompt change
- Cost regression → Evaluate token usage or fallback logic
- Latency regression → Inspect load or concurrency bottlenecks
- Execution error → Fix code or dependency configuration

No FAILED run should be manually forced to COMPLETED.

Rerun after fix.

---

## Operability Principle

SignalForge debugging is state-machine driven.

Every failure must be explainable in terms of:

- Explicit state transition
- Explicit failure category
- Explicit SLO or invariant violation

If a failure cannot be categorized, observability is insufficient and must be improved.