from typing import Any

from app.pipeline.run_pipeline import PipelineResult, run_pipeline


def enqueue_run(ticket: Any) -> PipelineResult:
    """Placeholder task queue entry point; synchronously runs the pipeline for now."""
    return run_pipeline(run_id="local", ticket=ticket)
