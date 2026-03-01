from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ORDER = ["graph", "bench", "dq", "qa", "run_contract", "manifest_integrity", "slo"]

GATE_COMMANDS: Dict[str, List[str]] = {
    "graph": [sys.executable, "-m", "sentinelqa.gates.graph_gate"],
    "bench": [sys.executable, "-m", "sentinelqa.gates.bench_gate"],
    "dq": [sys.executable, "-m", "sentinelqa.dq.run"],
    "qa": [sys.executable, "sentinelqa/gates/gate.py"],
    "run_contract": [sys.executable, "-m", "sentinelqa.gates.gate_run_contract"],
    "manifest_integrity": [sys.executable, "-m", "sentinelqa.gates.gate_manifest_integrity"],
    "slo": [sys.executable, "-m", "sentinelqa.gates.gate_slo"],
}


def _write_ledger(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(data, indent=2, sort_keys=True) + "\n"
    path.write_text(txt)


def _run_gate(name: str, cmd: List[str]) -> Tuple[str, int, str | None]:
    start = time.time()
    try:
        result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
        duration_ms = int((time.time() - start) * 1000)
        if result.returncode == 0:
            return "pass", duration_ms, None
        msg = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        return "fail", duration_ms, msg[:400]
    except Exception as exc:  # noqa: BLE001
        duration_ms = int((time.time() - start) * 1000)
        return "fail", duration_ms, str(exc)


def run_gate_sequence(
    run_id: str,
    run_dir: Path,
    required: List[str],
    gate_order: List[str] | None = None,
    gate_commands: Dict[str, List[str]] | None = None,
) -> Tuple[dict, str | None]:
    order = gate_order or DEFAULT_ORDER
    commands = gate_commands or GATE_COMMANDS

    ledger = {"version": 1, "run_id": run_id, "gates": []}
    ledger_path = run_dir / "gates.json"
    _write_ledger(ledger_path, ledger)

    failed_required: str | None = None
    for gate_name in order:
        if gate_name not in commands:
            raise ValueError(f"unknown gate {gate_name}")

        status, duration_ms, error = _run_gate(gate_name, commands[gate_name])
        entry = {
            "name": gate_name,
            "status": status,
            "duration_ms": duration_ms,
            "error": error,
        }
        ledger["gates"].append(entry)
        _write_ledger(ledger_path, ledger)

        if status != "pass" and gate_name in required:
            failed_required = gate_name
            break

    return ledger, failed_required


def _resolve_artifacts_root(arg_artifacts_dir: str | None) -> Path:
    if arg_artifacts_dir:
        return Path(arg_artifacts_dir)
    env_dir = os.getenv("ARTIFACTS_DIR")
    if env_dir:
        return Path(env_dir)
    return Path("artifacts")


def _discover_run_id(run_id_arg: str | None, artifacts_root: Path) -> Tuple[str, Path]:
    run_id = run_id_arg or os.getenv("RUN_ID")
    if not run_id:
        hint = artifacts_root / "latest_seed_run_id"
        if hint.exists():
            run_id = hint.read_text().strip()
    if not run_id:
        sys.exit(
            f"[FAIL] gate runner: missing run_id. Provide --run-id, set RUN_ID, or create {artifacts_root}/latest_seed_run_id."
        )
    run_dir = artifacts_root / "runs" / run_id
    if not run_dir.exists():
        sys.exit(f"[FAIL] gate runner: run artifacts not found at {run_dir}")
    return run_id, run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic gate runner with ledger output")
    parser.add_argument("--run-id", help="Run id (optional; resolved from RUN_ID env or artifacts/latest_seed_run_id)")
    parser.add_argument("--artifacts-dir", help="Artifacts root (default ARTIFACTS_DIR or ./artifacts)")
    parser.add_argument("--required", help="Comma-separated required gates", default=",".join(DEFAULT_ORDER))
    args = parser.parse_args()

    artifacts_root = _resolve_artifacts_root(args.artifacts_dir)
    run_id, run_dir = _discover_run_id(args.run_id, artifacts_root)
    required = [g for g in args.required.split(",") if g]

    ledger, failed = run_gate_sequence(run_id, run_dir, required)

    if failed:
        print(f"[FAIL] gate runner: {failed} failed")
        sys.exit(1)

    print(f"[OK] gate runner completed {len(ledger['gates'])} gates for run {run_id}")
    sys.exit(0)


if __name__ == "__main__":
    main()
