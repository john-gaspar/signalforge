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