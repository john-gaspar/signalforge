from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from jsonschema import Draft7Validator

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
REQUIRED_FILES = {
    "events.json": "events_v1.json",
    "clusters.json": "clusters_v1.json",
    "summary.json": "summary_v1.json",
    "alert.json": "alert_v1.json",
    "metrics.json": "metrics_v1.json",
}


def _load_schema(name: str) -> Dict[str, Any]:
    path = SCHEMA_DIR / name
    return json.loads(path.read_text())


def _resolve_artifacts_root(arg_artifacts_dir: str | None) -> Path:
    if arg_artifacts_dir:
        return Path(arg_artifacts_dir)
    env_dir = Path(__file__).resolve().parents[2] / "artifacts"
    return env_dir


def _discover_run(artifacts_root: Path, run_id_arg: str | None) -> Tuple[str, Path]:
    run_id = run_id_arg or (artifacts_root / "latest_seed_run_id").read_text().strip() if (artifacts_root / "latest_seed_run_id").exists() else None
    if not run_id:
        sys.exit("[FAIL] artifact schema: missing run_id (provide --run-id or artifacts/latest_seed_run_id)")
    run_dir = artifacts_root / "runs" / run_id
    if not run_dir.exists():
        sys.exit(f"[FAIL] artifact schema: run_dir missing at {run_dir}")
    return run_id, run_dir


def validate_artifacts(run_dir: Path) -> List[str]:
    errors: List[str] = []
    for rel, schema_name in REQUIRED_FILES.items():
        path = run_dir / rel
        if not path.exists():
            errors.append(f"{rel} missing")
            continue
        data = json.loads(path.read_text())
        schema = _load_schema(schema_name)
        v = Draft7Validator(schema)
        errs = sorted(v.iter_errors(data), key=lambda e: e.path)
        if errs:
            details = "; ".join([f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errs])
            errors.append(f"{rel} invalid: {details}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Artifact schema validation gate")
    parser.add_argument("--run-id", help="Run id (optional)")
    parser.add_argument("--artifacts-dir", help="Artifacts root (default ./artifacts)")
    args = parser.parse_args()

    artifacts_root = _resolve_artifacts_root(args.artifacts_dir)
    run_id, run_dir = _discover_run(artifacts_root, args.run_id)

    errors = validate_artifacts(run_dir)
    report = {
        "run_id": run_id,
        "version": 1,
        "errors": errors,
    }
    (run_dir / "schema_report.json").write_text(json.dumps(report, indent=2, sort_keys=True))

    if errors:
        print("[FAIL] artifact schema gate")
        for err in errors:
            print(f" - {err}")
        sys.exit(1)

    print("[PASS] artifact schema gate")
    sys.exit(0)


if __name__ == "__main__":
    main()
