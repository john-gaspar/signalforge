import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from redis import Redis
from rq import Queue

from app.core.config import settings
from app.core.db import get_db
from app.core.models import Run
from app.core.ids import make_run_id, stable_json
from app.jobs.tasks import process_run

router = APIRouter()

class ReplayRequest(BaseModel):
    fixtures_dir: str = Field(default="fixtures/tickets")
    fault_config: dict = Field(default_factory=dict)

@router.post("/replay")
def create_replay(req: ReplayRequest, db: Session = Depends(get_db)):
    config = {"fixtures_dir": req.fixtures_dir, "fault_config": req.fault_config}

    # Idempotency: same config => same idempotency_key => prevents dup runs
    idempotency_key = f"replay:{stable_json(config)}"
    run_id = make_run_id(idempotency_key)

    existing = db.get(Run, run_id)
    if existing:
        return {"run_id": existing.run_id, "status": existing.status, "idempotent": True}

    run = Run(run_id=run_id, mode="replay", status="queued", config=config, idempotency_key=idempotency_key)
    db.add(run)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        # Unique constraint race: fetch existing
        existing = db.get(Run, run_id)
        if existing:
            return {"run_id": existing.run_id, "status": existing.status, "idempotent": True}
        raise

    redis_conn = Redis.from_url(settings.redis_url)
    q = Queue(settings.rq_queue_name, connection=redis_conn)
    job = q.enqueue(process_run, run_id, job_id=run_id)  # job_id = run_id for traceability

    return {"run_id": run_id, "status": "queued", "job_id": job.id}

@router.get("/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "run_id": run.run_id,
        "mode": run.mode,
        "status": run.status,
        "config": run.config,
        "metrics": run.metrics,
        "error": run.error,
        "created_at": run.created_at,
        "started_at": run.started_at,
        "ended_at": run.ended_at,
    }