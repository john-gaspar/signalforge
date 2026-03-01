from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Tuple

ALLOWED_FAILURE_CATEGORIES = {"none", "pipeline_error", "data_quality", "perf", "graph", "unknown", "infra.redis", "infra.neo4j", "artifact.integrity"}
DEFAULT_RUN_MAX_MS = 60000


def _latest_run_dir(artifacts_root: Path) -> Tuple[Path | None, str | None]:
    hint = Path("artifacts/latest_seed_run_id")
    if hint.exists():
        run_id = hint.read_text().strip()
        run_dir = artifacts_root / run_id
        if run_dir.exists():
            return run_dir, run_id

    metrics_files = sorted(
        artifacts_root.glob("**/metrics.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not metrics_files:
        return None, None
    metrics_path = metrics_files[0]
    return metrics_path.parent, metrics_path.parent.name


def _load_metadata(run_dir: Path) -> dict[str, Any]:
    meta_path = run_dir / "run_metadata.json"
    if not meta_path.exists():
        raise RuntimeError(f"run_metadata.json missing at {meta_path}")
    return json.loads(meta_path.read_text())


def validate_slo(metadata: dict[str, Any], max_ms: int) -> list[str]:
    errors: list[str] = []
    required_fields = ["run_id", "run_duration_ms", "final_status", "state_transition_path", "gate_results", "failure_category"]
    missing = [f for f in required_fields if f not in metadata]
    if missing:
        errors.append(f"missing fields: {', '.join(missing)}")
        return errors

    duration = metadata.get("run_duration_ms")
    if duration is None or not isinstance(duration, (int, float)):
        errors.append("run_duration_ms must be numeric")
    elif duration > max_ms:
        errors.append(f"run_duration_ms {duration} > max {max_ms}")

    failure_category = str(metadata.get("failure_category") or "none")
    if failure_category not in ALLOWED_FAILURE_CATEGORIES:
        errors.append(f"failure_category {failure_category} not allowed")
    final_status = metadata.get("final_status")
    if final_status == "succeeded" and failure_category != "none":
        errors.append("succeeded run must have failure_category=none")
    if final_status == "failed" and failure_category == "none":
        errors.append("failed run must set failure_category")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="SLO gate enforcing run metadata guarantees")
    parser.add_argument("--artifacts-root", default="artifacts/runs")
    parser.add_argument("--max-ms", type=int, default=None, help="Override max runtime in ms")
    args = parser.parse_args()

    artifacts_root = Path(args.artifacts_root)
    run_dir, run_id = _latest_run_dir(artifacts_root)
    if not run_dir or not run_id:
        sys.exit("No run artifacts found; cannot enforce SLOs")

    try:
        metadata = _load_metadata(run_dir)
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        sys.exit(1)

    max_ms = args.max_ms if args.max_ms is not None else int(os.getenv("SLO_RUN_MAX_MS", DEFAULT_RUN_MAX_MS))
    errors = validate_slo(metadata, max_ms)
    if errors:
        print("[FAIL] slo gate")
        for err in errors:
            print(f" - {err}")
        sys.exit(1)

    print("[PASS] slo gate")
    sys.exit(0)


if __name__ == "__main__":
    main()
