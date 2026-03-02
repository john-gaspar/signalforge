from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _latest_entry_exists(history_path: Path, run_id: str) -> bool:
    if not history_path.exists():
        return False
    # Check from end for efficiency; first match means already recorded.
    for line in reversed(history_path.read_text().splitlines()):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("run_id") == run_id:
            return True
    return False


def append_bench_history(result_path: Path, history_path: Path, now: datetime | None = None) -> None:
    """Append latest bench metrics to history.jsonl, deduplicated by run_id."""

    if not result_path.exists():
        raise FileNotFoundError(f"bench result not found at {result_path}")

    result = json.loads(result_path.read_text())
    run_id = result.get("run_id")
    if not run_id:
        raise ValueError("bench result missing run_id")

    entry = {
        "timestamp": (now or datetime.now(timezone.utc)).isoformat(),
        "run_id": run_id,
        "f1": float(result.get("accuracy", {}).get("f1", 0.0)),
        "pass_rate": float(result.get("cases_succeeded", 0) / max(result.get("cases_total", 1), 1)),
        "p95_latency_ms": float(result.get("p95_latency_ms", 0.0)),
    }

    history_path.parent.mkdir(parents=True, exist_ok=True)
    if _latest_entry_exists(history_path, run_id):
        return

    with history_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
