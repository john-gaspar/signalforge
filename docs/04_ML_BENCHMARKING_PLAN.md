# ML Benchmarking Plan (Even with Stub Logic)

## Objective

Demonstrate ML output validation discipline.

Even if logic is stubbed, we simulate model evaluation rigor.

---

## Golden Dataset

fixtures/golden/
Contains:
- Expected cluster IDs
- Expected alert_sent label

---

## Metrics

Classification:
- Precision
- Recall
- F1 score

Performance:
- p50 latency
- p95 latency

Stability:
- cluster_count delta

---

## Regression Rules

Fail CI if:
- F1 < baseline_f1
- p95 > baseline_p95
- cluster_count deviation > tolerance

---

## Deliverable

Command:
python -m sentinelqa.bench.run

Produces:
- JSON report
- Exit code 1 on regression