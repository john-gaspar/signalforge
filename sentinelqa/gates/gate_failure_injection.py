from __future__ import annotations

import json
import os
import shutil
import socket
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

from sentinelqa.artifacts.manifest import write_manifest, validate_manifest


def _artifacts_root(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    env_dir = os.getenv("ARTIFACTS_DIR")
    return Path(env_dir) if env_dir else Path("artifacts")


def _resolve_run_dir(artifacts_root: Path, run_id_arg: str | None) -> Tuple[str, Path]:
    run_id = run_id_arg or os.getenv("RUN_ID")
    if not run_id:
        hint = artifacts_root / "latest_seed_run_id"
        if hint.exists():
            run_id = hint.read_text().strip()
    if not run_id:
        raise RuntimeError(f"missing run_id; set RUN_ID or create {artifacts_root}/latest_seed_run_id")
    run_dir = artifacts_root / "runs" / run_id
    if not run_dir.exists():
        raise RuntimeError(f"run artifacts not found at {run_dir}")
    return run_id, run_dir


def _scenario_socket_unavailable(name: str, host: str, port: int, category: str) -> Dict[str, str]:
    try:
        with socket.create_connection((host, port), timeout=1):
            return {"name": name, "status": "fail", "category": category, "detail": "unexpectedly connected"}
    except Exception as exc:  # noqa: BLE001
        return {"name": name, "status": "pass", "category": category, "detail": f"connect failed as expected: {exc}"}


def _scenario_artifact_tamper(run_id: str, run_dir: Path) -> Dict[str, str]:
    # copy run artifacts to temp, tamper, then validate manifest expecting failure
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir) / "artifacts"
        tmp_run_dir = tmp_root / "runs" / run_id
        shutil.copytree(run_dir, tmp_run_dir)
        # ensure manifest exists; create if missing
        manifest_path = tmp_run_dir / "manifest.json"
        if not manifest_path.exists():
            write_manifest(tmp_run_dir, run_id, ["events.json", "clusters.json", "summary.json", "alert.json", "metrics.json"])
        # tamper a file
        events_path = tmp_run_dir / "events.json"
        if events_path.exists():
            events_path.write_text(events_path.read_text() + "\n {\"tamper\": true}\n")
        errors = validate_manifest(manifest_path)
        if errors:
            return {
                "name": "artifact_tamper",
                "status": "pass",
                "category": "artifact.integrity",
                "detail": "; ".join(errors)[:400],
            }
        return {
            "name": "artifact_tamper",
            "status": "fail",
            "category": "artifact.integrity",
            "detail": "manifest validation unexpectedly passed after tamper",
        }


def run_failure_injection(run_id: str, run_dir: Path) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    results.append(_scenario_socket_unavailable("redis_unavailable", "redis.invalid", 6379, "infra.redis"))
    results.append(_scenario_socket_unavailable("neo4j_unavailable", "neo4j.invalid", 7687, "infra.neo4j"))
    results.append(_scenario_artifact_tamper(run_id, run_dir))
    return results


def main() -> None:
    if os.getenv("FAILURE_INJECTION") != "1":
        print("[SKIP] failure injection gate (set FAILURE_INJECTION=1 to enable)")
        sys.exit(0)

    artifacts_root = _artifacts_root(None)
    try:
        run_id, run_dir = _resolve_run_dir(artifacts_root, None)
    except RuntimeError as exc:
        print(f"[FAIL] failure injection gate: {exc}")
        sys.exit(1)

    results = run_failure_injection(run_id, run_dir)
    report_dir = artifacts_root / "failure_injection"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "report.json").write_text(json.dumps({"run_id": run_id, "results": results}, indent=2, sort_keys=True))

    failures = [r for r in results if r["status"] != "pass"]
    if failures:
        print("[FAIL] failure injection gate")
        for r in failures:
            print(f" - {r['name']}: {r['detail']}")
        sys.exit(1)

    print("[PASS] failure injection gate")
    sys.exit(0)


if __name__ == "__main__":
    main()
