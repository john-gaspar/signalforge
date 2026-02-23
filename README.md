# SignalForge

Lightweight replay pipeline with FastAPI, RQ, Postgres, Redis, and stubbed pipeline stages plus a QA gate script.

## Quick start
1. Copy env: `cp .env.example .env` and fill values.
2. Start backing services: `docker compose up -d postgres redis`.
3. Run API + worker (separate terminals):
   - API: `docker compose up api`
   - Worker: `docker compose up worker`
4. Add fixtures in `fixtures/tickets/*.json`.
5. Trigger a replay run:
   ```bash
   curl -X POST http://localhost:8000/runs/replay \
     -H "Content-Type: application/json" \
     -d '{"fixtures_dir":"fixtures/tickets","fault_config":{}}'
   ```
6. Check status: `curl http://localhost:8000/runs/<run_id>`.
7. Inspect artifacts: `artifacts/runs/<run_id>/`.
8. QA gate (local venv): `python sentinelqa/gates/gate.py`.
   - Containerized gate (CI parity): `docker compose run --rm api python sentinelqa/gates/gate.py`.

## Environment variables
- `DATABASE_URL` (e.g., `postgresql+psycopg://signalforge:signalforge@postgres:5432/signalforge`)
- `REDIS_URL` (e.g., `redis://redis:6379/0`)
- `ARTIFACTS_DIR` (default `/code/artifacts` in Docker, `./artifacts` locally)
- `RQ_QUEUE_NAME` (default `signalforge`)

## QA thresholds
Defined in `sentinelqa/gates/thresholds.yaml` (e.g., latency max, alerts_sent min).

## Notes
- Idempotent run creation: same config => same `run_id`.
- Pipeline writes artifacts and metrics under `artifacts/runs/<run_id>/`.
- Stubs: stages are deterministic placeholders; replace with real logic as needed.
