from dataclasses import dataclass
from typing import Any, Callable, Iterable, List

from app.pipeline.stages_stub import DEFAULT_STAGES


@dataclass
class PipelineResult:
    run_id: str
    status: str
    history: List[str]
    output: Any


Stage = Callable[[Any], Any]


def run_pipeline(run_id: str, ticket: Any, stages: Iterable[Stage] = DEFAULT_STAGES) -> PipelineResult:
    """Run through each stage, passing along the mutable ticket payload."""
    history: List[str] = []
    payload = ticket

    for stage in stages:
        stage_name = getattr(stage, "__name__", "stage")
        history.append(f"starting:{stage_name}")
        payload = stage(payload)
        history.append(f"finished:{stage_name}")

    return PipelineResult(run_id=run_id, status="completed", history=history, output=payload)
