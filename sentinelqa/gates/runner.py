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


def _discover_run_id(run_id_arg: str | None) -> Tuple[str, Path]:
    if run_id_arg:
        run_id = run_id_arg
    else:
        hint = Path("artifacts/latest_seed_run_id")
        if not hint.exists():
            raise RuntimeError("run-id not provided and artifacts/latest_seed_run_id missing")
        run_id = hint.read_text().strip()
    run_dir = Path("artifacts/runs") / run_id
    if not run_dir.exists():
        raise RuntimeError(f"run artifacts not found at {run_dir}")
    return run_id, run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic gate runner with ledger output")
    parser.add_argument("--run-id", help="Run id (defaults to artifacts/latest_seed_run_id)")
    parser.add_argument("--artifacts-dir", help="Artifacts run dir (defaults to artifacts/runs/<run_id>)")
    parser.add_argument("--required", help="Comma-separated required gates", default=",".join(DEFAULT_ORDER))
    args = parser.parse_args()

    run_id, auto_run_dir = _discover_run_id(args.run_id)
    run_dir = Path(args.artifacts_dir) if args.artifacts_dir else auto_run_dir
    required = [g for g in args.required.split(",") if g]

    ledger, failed = run_gate_sequence(run_id, run_dir, required)

    if failed:
        print(f"[FAIL] gate runner: {failed} failed")
        sys.exit(1)

    print(f"[OK] gate runner completed {len(ledger['gates'])} gates for run {run_id}")
    sys.exit(0)


if __name__ == "__main__":
    main()
