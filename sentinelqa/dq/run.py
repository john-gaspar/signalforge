from __future__ import annotations

import json
import sys
from pathlib import Path
import os

from sentinelqa.dq.checks import (
    check_artifact_invariants,
    check_db_invariant,
    validate_fixtures,
)
from sentinelqa.dq import drift


def _latest_run_dir() -> tuple[Path | None, str | None]:
    hint_file = Path("artifacts/latest_seed_run_id")
    if hint_file.exists():
        run_id = hint_file.read_text().strip()
        run_dir = Path("artifacts/runs") / run_id
        if run_dir.exists():
            return run_dir, run_id

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

    env = os.environ
    ci_mode = env.get("CI", "").lower() == "true"

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

        # Drift detection
        drift_mode = env.get("DQ_DRIFT_MODE") or ("fail" if ci_mode else "warn")
        baseline_path = Path(env.get("DQ_DRIFT_BASELINE", "sentinelqa/baselines/drift_baseline.json"))
        require_baseline = env.get("DQ_REQUIRE_DRIFT_BASELINE") == "1"

        if not baseline_path.exists():
            msg = f"baseline missing at {baseline_path}"
            if drift_mode == "fail" and require_baseline:
                _print_result("drift detection", "FAIL", msg)
                failures.append("drift detection")
            else:
                _print_result("drift detection", "SKIP", msg)
            # do not proceed without baseline
        else:
            baseline = json.loads(baseline_path.read_text())
            current = drift.compute_summary(run_dir)
            diffs = drift.compare(baseline, current)
            if diffs:
                detail_msg = "; ".join(diffs)
                status = "FAIL" if drift_mode == "fail" else "WARN"
                _print_result("drift detection", status, detail_msg)
                if drift_mode == "fail":
                    failures.append("drift detection")
            else:
                _print_result("drift detection", "PASS")

    if failures:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
