# Load Testing Plan

## Objective

Validate system behaviour under concurrency.

---

## Tool

Locust

---

## Scenarios

1. 50 concurrent replay requests
2. 100 concurrent replay requests
3. Mixed fixture sizes

---

## Metrics to Capture

- API response time
- Worker throughput (jobs/min)
- p95 latency
- Failure rate

---

## Acceptance Criteria

System maintains:
- < 2% failure rate
- Stable latency curve
- No worker crash

---

## Interview Talking Point

"I validate both correctness and scalability.
I measure throughput and latency under load,
not just functional behaviour."