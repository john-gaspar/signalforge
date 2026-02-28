# SignalForge

Lightweight replay pipeline with FastAPI, RQ, Postgres, Redis, and stubbed pipeline stages plus a QA gate script.

## Quick start
1. Copy env: `cp .env.example .env` and fill values.
2. Start backing services: `docker compose up -d postgres redis`.
3. Run DB migrations (once): `docker compose run --rm api alembic upgrade head`.
4. Run API + worker (separate terminals):
   - API: `docker compose up api`
   - Worker: `docker compose up worker`
5. Add fixtures in `fixtures/tickets/*.json`.
6. Trigger a replay run:
   ```bash
   curl -X POST http://localhost:8000/runs/replay \
     -H "Content-Type: application/json" \
     -d '{"fixtures_dir":"fixtures/tickets","fault_config":{}}'
   ```
7. Check status: `curl http://localhost:8000/runs/<run_id>`.
8. Inspect artifacts: `artifacts/runs/<run_id>/`.
9. QA gate (local venv): `python3 sentinelqa/gates/gate.py`.
   - Containerized gate (CI parity): `docker compose run --rm api python sentinelqa/gates/gate.py`.
10. Data Quality gate: `python -m sentinelqa.dq.run`

## Migrations (Alembic)
- Upgrade to latest: `docker compose run --rm api alembic upgrade head`
- Create revision (autogenerate): `docker compose run --rm api alembic revision --autogenerate -m "..."`

## Data Quality Gate
- Run locally: `python -m sentinelqa.dq.run`

## Preflight
- `./scripts/preflight.sh` (compileall + optional actionlint/ruff)

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

## Portfolio story (shift-left QA)
- Purpose: demonstrate building a quality harness in parallel with feature dev—fixtures, deterministic pipeline, metrics-based gate, and CI wiring that will later wrap real APIs and ML/HF models.
- What’s here: replay endpoint using fixture tickets, stub stages, artifact/metrics generation, QA gate enforced in CI, placeholder pytest scaffold.
- How to evolve: swap stub stages for real integrations (APIs, Hugging Face models), add more fixtures (anonymized/captured), broaden thresholds, and grow pytest suites (unit, integration, e2e).
- CI contract: seed run → QA gate → pytest. This stays stable as logic becomes “real,” keeping regressions visible early.
- Workflow: solo is fine to commit to `main`; if collaborators join, use short-lived branches/PRs so QA gate and tests run on every change.
