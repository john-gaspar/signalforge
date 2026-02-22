from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException

from app.core.ids import generate_run_id
from app.core.models import Run
from app.pipeline.run_pipeline import run_pipeline

router = APIRouter()


@router.get("/runs", response_model=List[Run])
def list_runs() -> List[Run]:
    """Return a synthetic list of runs. Replace with DB-backed listing later."""
    placeholder = Run(id=generate_run_id(), status="queued", created_at=datetime.utcnow())
    return [placeholder]


@router.post("/runs", response_model=Run, status_code=201)
def create_run(ticket: dict) -> Run:
    """Kick off a new run for a provided ticket payload."""
    if not isinstance(ticket, dict):
        raise HTTPException(status_code=400, detail="ticket must be an object")

    run_id = generate_run_id()
    run_result = run_pipeline(run_id=run_id, ticket=ticket)
    return Run(id=run_id, status=run_result.status, created_at=datetime.utcnow())
