from __future__ import annotations

import json
import sys
from pathlib import Path

from sentinelqa.dq.checks import (
    check_artifact_invariants,
    check_db_invariant,
    validate_fixtures,
)


def _latest_run_dir() -> tuple[Path | None, str | None]:
    artifacts_root = Path("artifacts/runs")
    metrics_files = sorted(
        artifacts_root.glob("**/metrics.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not metrics_files:
        return None, None
    metrics_path = metrics_files[0]
    return metrics_path.parent, metrics_path.parent.name


def _print_result(label: str, status: str, detail: str | None = None):
    if detail:
        print(f"[{status}] {label}: {detail}")
    else:
        print(f"[{status}] {label}")


def main():
    failures = []

    # Fixture schema
    ok, detail = validate_fixtures()
    _print_result("fixture schema", "PASS" if ok else "FAIL", detail)
    if not ok:
        failures.append("fixture schema")

    # Locate latest run
    run_dir, run_id = _latest_run_dir()
    if run_dir is None or run_id is None:
        _print_result("artifact invariants", "FAIL", "no artifacts/runs/*/metrics.json found")
        failures.append("artifact invariants")
    else:
        ok, detail = check_artifact_invariants(run_dir, run_id)
        _print_result("artifact invariants", "PASS" if ok else "FAIL", detail)
        if not ok:
            failures.append("artifact invariants")

        status, detail = check_db_invariant(run_id)
        if status == "pass":
            _print_result("db invariant", "PASS")
        elif status == "skip":
            _print_result("db invariant", "SKIP", detail)
        else:
            _print_result("db invariant", "FAIL", detail)
            failures.append("db invariant")

    if failures:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
