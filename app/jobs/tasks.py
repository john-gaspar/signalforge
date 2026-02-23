import os
import time
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.models import Run
from app.pipeline.run_pipeline import run_pipeline

def process_run(run_id: str) -> None:
    db: Session = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if not run:
            return

        # If re-run happens, idempotency is enforced at creation time (unique key)
        run.status = "running"
        run.started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        db.commit()

        metrics = run_pipeline(run_id=run_id, config=run.config)

        run.status = "succeeded"
        run.metrics = metrics
        run.ended_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        db.commit()
    except Exception as e:
        run = db.get(Run, run_id)
        if run:
            run.status = "failed"
            run.error = {"type": type(e).__name__, "message": str(e)}
            run.ended_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            db.commit()
        raise
    finally:
        db.close()