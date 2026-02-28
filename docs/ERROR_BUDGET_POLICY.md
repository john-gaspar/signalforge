# Error Budget Policy

## Objective

Define explicit reliability tolerances for SignalForge + SentinelQA.

Error budgets formalise how much failure is acceptable before engineering intervention is required.

This prevents:

- Silent degradation
- Unbounded cost growth
- Latency creep
- Accuracy drift

Error budgets are measurable, enforceable, and tied to CI gating.

---

# Core Principle

Reliability is not binary (working / broken).

Reliability is a bounded risk envelope.

If the system exceeds defined thresholds, it is considered degraded — even if it still “works”.

---

# SLO Domains

SignalForge defines SLOs across four domains:

1. Availability  
2. Performance  
3. Quality  
4. Cost  

Each domain has:

- Numeric target
- Measurement method
- Budget window
- Severity classification

---

# 1️⃣ Availability Error Budget

## SLO

- API availability ≥ 99%
- Worker job success rate ≥ 99%

## Budget

1% failure budget per rolling evaluation window.

If error rate exceeds 1%:
- CI blocks merges
- Investigation required
- Baseline cannot be updated

---

# 2️⃣ Performance Error Budget

## SLO

- p95 latency ≤ baseline_p95 * 1.20
- Queue wait time within defined threshold

## Budget

- >20% regression → FAIL
- 10–20% regression → WARN

Repeated WARN across 3 runs escalates to FAIL.

---

# 3️⃣ Quality Error Budget

## SLO

- Accuracy drop ≤ 2%
- Label distribution divergence ≤ defined threshold
- Structural invariants = 100% pass

## Budget

- Accuracy drop > 2% → FAIL
- Divergence above threshold → FAIL
- Any structural invariant violation → FAIL

No tolerance for structural integrity failure.

---

# 4️⃣ Cost Error Budget

## SLO

- Cost per run ≤ baseline_cost * 1.15
- Token usage variance within tolerance

## Budget

- >15% cost increase → FAIL
- 10–15% increase → WARN

Cost regressions are treated as reliability violations.

---

# CI Enforcement Rules

CI must:

- Exit non-zero on FAIL
- Log WARN events explicitly
- Prevent baseline promotion when FAIL occurs

No code merge may introduce FAIL-level regression.

---

# Budget Escalation Policy

If a FAIL occurs:

1. Run marked degraded
2. Root cause required
3. Fix or revert required before merge
4. Baseline remains unchanged

If WARN persists across multiple runs:
- Escalate to FAIL threshold

---

# Design Philosophy

Error budgets:

- Prevent complacency
- Quantify acceptable degradation
- Align engineering discipline with production risk
- Convert ML benchmarking into enforceable governance

SentinelQA enforces reliability — not just correctness.