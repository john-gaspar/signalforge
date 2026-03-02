from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Tuple

from sentinelqa.artifacts.manifest import write_manifest
from sentinelqa.ci import seed_run

REQUIRED_FILES = ["tickets.json", "events.json", "clusters.json", "summary.json", "alert.json", "metrics.json"]


def _artifacts_root(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    env_dir = os.getenv("ARTIFACTS_DIR")
    return Path(env_dir) if env_dir else Path("artifacts")


def _run_once(base_url: str, artifacts_root: Path) -> str:
    seed_run._wait_api_ready(base_url)  # type: ignore[attr-defined]
    run_id = seed_run._post_run(base_url, {"fixtures_dir": "fixtures/tickets", "fault_config": {}})  # type: ignore[attr-defined]
    seed_run._wait_run(base_url, run_id)  # type: ignore[attr-defined]
    try:
        artifacts_root.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return run_id


def _load_manifest(run_dir: Path, run_id: str) -> Dict:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        write_manifest(run_dir, run_id, REQUIRED_FILES)
    return json.loads(manifest_path.read_text())


def _compare_runs(run_a: Tuple[str, Path], run_b: Tuple[str, Path]) -> Dict[str, object]:
    (run_id_a, dir_a), (run_id_b, dir_b) = run_a, run_b
    man_a = _load_manifest(dir_a, run_id_a)
    man_b = _load_manifest(dir_b, run_id_b)

    fingerprint_equal = man_a.get("fingerprint_sha256") == man_b.get("fingerprint_sha256")

    metrics_equal = False
    try:
        metrics_equal = json.loads((dir_a / "metrics.json").read_text()) == json.loads((dir_b / "metrics.json").read_text())
    except Exception:
        metrics_equal = False

    gates_equal = True
    gates_a = dir_a / "gates.json"
    gates_b = dir_b / "gates.json"
    if gates_a.exists() and gates_b.exists():
        try:
            ga = json.loads(gates_a.read_text())
            gb = json.loads(gates_b.read_text())
            ga_set = {(g.get("name"), g.get("status")) for g in ga.get("gates", [])}
            gb_set = {(g.get("name"), g.get("status")) for g in gb.get("gates", [])}
            gates_equal = ga_set == gb_set
        except Exception:
            gates_equal = False

    return {
        "run_a": run_id_a,
        "run_b": run_id_b,
        "fingerprint_equal": fingerprint_equal,
        "fingerprint_a": man_a.get("fingerprint_sha256"),
        "fingerprint_b": man_b.get("fingerprint_sha256"),
        "metrics_equal": metrics_equal,
        "gates_equal": gates_equal,
    }


def main() -> None:
    if os.getenv("DETERMINISTIC_REPLAY") != "1":
        print("[SKIP] deterministic replay gate (set DETERMINISTIC_REPLAY=1 to enable)")
        sys.exit(0)

    artifacts_root = _artifacts_root(None)
    base_url = os.getenv("DETERMINISTIC_REPLAY_BASE_URL", "http://api:8000")

    try:
        run_id_a = _run_once(base_url, artifacts_root)
        run_id_b = _run_once(base_url, artifacts_root)
    except Exception as exc:
        print(f"[FAIL] deterministic replay gate: failed to create runs ({exc})")
        sys.exit(1)

    report = _compare_runs(
        (run_id_a, artifacts_root / "runs" / run_id_a),
        (run_id_b, artifacts_root / "runs" / run_id_b),
    )

    report_dir = artifacts_root / "replay"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True))

    if not (report["fingerprint_equal"] and report["metrics_equal"] and report["gates_equal"]):
        print("[FAIL] deterministic replay gate")
        print(
            f" run_a={report['run_a']} fp={report['fingerprint_a']} | run_b={report['run_b']} fp={report['fingerprint_b']}"
        )
        print(f" metrics_equal={report['metrics_equal']} gates_equal={report['gates_equal']}")
        sys.exit(1)

    print("[PASS] deterministic replay gate")
    sys.exit(0)


if __name__ == "__main__":
    main()
