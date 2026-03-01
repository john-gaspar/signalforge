from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from sentinelqa.dq.checks import check_artifact_invariants
from sentinelqa.artifacts.manifest import write_manifest

REQUIRED_FILES = [
    "events.json",
    "clusters.json",
    "summary.json",
    "alert.json",
    "metrics.json",
]
LEDGER_FILE = "gates.json"


def _iso_to_dt(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        cleaned = val.replace("Z", "+00:00") if val.endswith("Z") else val
        try:
            return datetime.fromisoformat(cleaned)
        except ValueError:
            return None
    return None


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


def _load_run_record_from_db(run_id: str) -> Dict[str, Any]:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL not set; cannot load run record")

    engine = create_engine(db_url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT run_id, status, created_at, started_at, ended_at, metrics, error "
                    "FROM runs WHERE run_id = :run_id"
                ),
                {"run_id": run_id},
            ).mappings().first()
            if not row:
                raise RuntimeError(f"run {run_id} not found in database")
            return dict(row)
    except SQLAlchemyError as exc:
        raise RuntimeError(f"database error: {exc}") from exc


def _load_run_record(run_id: str, record_path: Path | None) -> Dict[str, Any]:
    if record_path:
        data = json.loads(record_path.read_text())
        if data.get("run_id") and data["run_id"] != run_id:
            raise RuntimeError(f"run_id mismatch between record ({data['run_id']}) and artifacts ({run_id})")
        data.setdefault("run_id", run_id)
        return data
    return _load_run_record_from_db(run_id)


def _validate_state_transitions(run: Dict[str, Any], max_clock_skew_s: int) -> List[str]:
    errors: List[str] = []
    status = run.get("status")
    created_at = _iso_to_dt(run.get("created_at"))
    started_at = _iso_to_dt(run.get("started_at"))
    ended_at = _iso_to_dt(run.get("ended_at"))

    if status not in {"queued", "running", "succeeded", "failed"}:
        errors.append(f"invalid status {status}")

    if status in {"running", "succeeded", "failed"} and started_at is None:
        errors.append("started_at missing for state requiring start")
    if status in {"succeeded", "failed"} and ended_at is None:
        errors.append("ended_at missing for terminal state")
    if status == "succeeded" and run.get("metrics") is None:
        errors.append("succeeded run missing metrics")
    if status == "succeeded" and run.get("error"):
        errors.append("succeeded run should not carry error")
    if status == "failed":
        err = run.get("error")
        if not err:
            errors.append("failed run missing error")
        elif not isinstance(err, dict) or not err.get("type") and not err.get("message"):
            errors.append("failed run error missing failure_reason detail")

    # Order checks only if timestamps are parseable; allow small skew between DB clock and app clock.
    if created_at and started_at and started_at < created_at:
        skew_s = (created_at - started_at).total_seconds()
        if skew_s > max_clock_skew_s:
            errors.append(
                f"started_at earlier than created_at by {int(skew_s)}s (max skew {max_clock_skew_s}s)"
            )
        else:
            print(f"[WARN] clock skew detected: started_at {started_at} before created_at {created_at} by {int(skew_s)}s")
    if started_at and ended_at and ended_at < started_at:
        errors.append("ended_at earlier than started_at")

    return errors


def _validate_artifacts(run_dir: Path, run_id: str) -> List[str]:
    errors: List[str] = []
    manifest = sorted(p.name for p in run_dir.glob("*.json"))
    missing = [f for f in REQUIRED_FILES if f not in manifest]
    if missing:
        errors.append(f"artifact manifest missing: {', '.join(missing)}")

    ok, detail = check_artifact_invariants(run_dir, run_id)
    if not ok:
        errors.append(f"artifact invariant failure: {detail}")

    return errors


def _validate_gate_results(run_id: str, bench_report: Path, require_bench: bool) -> List[str]:
    errors: List[str] = []
    if bench_report.exists():
        data = json.loads(bench_report.read_text())
        report_run_id = data.get("run_id")
        if not report_run_id:
            errors.append("bench report missing run_id")
    elif require_bench:
        errors.append(f"bench report missing at {bench_report}")
    return errors


def _load_gate_results(run_dir: Path) -> List[dict[str, Any]]:
    ledger_path = run_dir / LEDGER_FILE
    if not ledger_path.exists():
        return []
    try:
        data = json.loads(ledger_path.read_text())
        gates = data.get("gates")
        return gates if isinstance(gates, list) else []
    except Exception:
        return []


def _write_run_metadata(run_dir: Path, run_record: Dict[str, Any], gate_results: List[dict[str, str]]) -> None:
    started = _iso_to_dt(run_record.get("started_at"))
    ended = _iso_to_dt(run_record.get("ended_at"))
    duration_ms: int | None = None
    if started and ended:
        duration_ms = int((ended - started).total_seconds() * 1000)

    status = run_record.get("status")
    path: List[str] = ["queued"]
    if started:
        path.append("running")
    if status:
        path.append(status)

    error = run_record.get("error") or {}
    failure_category = "none"
    if status == "failed":
        failure_category = str(error.get("type") or error.get("message") or "unknown").lower()
        allowed = {"pipeline_error", "data_quality", "perf", "graph", "unknown"}
        if failure_category not in allowed:
            failure_category = "unknown"

    payload = {
        "run_id": run_record.get("run_id"),
        "run_duration_ms": duration_ms,
        "final_status": status,
        "state_transition_path": path,
        "gate_results": gate_results,
        "failure_category": failure_category,
    }
    out_path = run_dir / "run_metadata.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def validate_run_contract(
    run_dir: Path,
    run_record: Dict[str, Any],
    bench_report: Path,
    require_bench: bool,
    max_clock_skew_s: int | None = None,
) -> List[str]:
    errors: List[str] = []
    max_skew = max_clock_skew_s if max_clock_skew_s is not None else int(os.getenv("RUN_CONTRACT_MAX_CLOCK_SKEW_S", "300"))
    errors += _validate_state_transitions(run_record, max_skew)
    errors += _validate_artifacts(run_dir, run_record["run_id"])
    errors += _validate_gate_results(run_record["run_id"], bench_report, require_bench)
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Contract Gate")
    parser.add_argument("--run-id")
    parser.add_argument("--run-record", help="Path to JSON run record (for testing/offline)")
    parser.add_argument("--artifacts-root", default="artifacts/runs")
    parser.add_argument("--bench-report", default="artifacts/bench/latest.json")
    parser.add_argument("--skip-bench", action="store_true", help="Do not require bench report")
    args = parser.parse_args()

    artifacts_root = Path(args.artifacts_root)
    run_dir, discovered_run_id = _latest_run_dir(artifacts_root) if not args.run_id else (artifacts_root / args.run_id, args.run_id)
    if not run_dir or not discovered_run_id or not run_dir.exists():
        sys.exit("No run artifacts found; cannot validate run contract")

    try:
        record_path = Path(args.run_record) if args.run_record else None
        run_record = _load_run_record(discovered_run_id, record_path)
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        sys.exit(1)

    bench_report = Path(args.bench_report)
    require_bench = not args.skip_bench and os.getenv("RUN_CONTRACT_REQUIRE_BENCH", "1") != "0"

    errors = validate_run_contract(run_dir, run_record, bench_report, require_bench)
    if errors:
        print("[FAIL] run contract")
        for err in errors:
            print(f" - {err}")
        sys.exit(1)

    gate_results = _load_gate_results(run_dir)
    _write_run_metadata(run_dir, run_record, gate_results)
    try:
        write_manifest(run_dir, run_record["run_id"], REQUIRED_FILES)
    except Exception as exc:
        print(f"[FAIL] manifest write: {exc}")
        sys.exit(1)
    print("[PASS] run contract")
    sys.exit(0)


if __name__ == "__main__":
    main()
