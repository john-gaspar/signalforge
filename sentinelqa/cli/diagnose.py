from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


EVIDENCE_FILES = {
    "gates": "gates.json",
    "run_metadata": "run_metadata.json",
    "manifest": "manifest.json",
    "schema_report": "schema_report.json",
    "bench": "../bench/latest.json",  # relative to run dir
    "replay": "../replay/report.json",  # relative to artifacts root
}


def _artifacts_root(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    return Path("artifacts")


def _resolve_run_id(run_id_arg: str | None, artifacts_root: Path) -> Tuple[str, Path]:
    run_id = run_id_arg
    if not run_id:
        hint = artifacts_root / "latest_seed_run_id"
        if hint.exists():
            run_id = hint.read_text().strip()
    if not run_id:
        sys.exit("Missing run_id; provide --run-id or ensure artifacts/latest_seed_run_id exists.")
    run_dir = artifacts_root / "runs" / run_id
    if not run_dir.exists():
        sys.exit(f"Run artifacts not found at {run_dir}")
    return run_id, run_dir


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _summarize_gates(gates_path: Path) -> Tuple[List[Dict[str, str]], str | None]:
    data = _load_json(gates_path) or {}
    gate_entries = data.get("gates", [])
    first_fail = None
    summary = []
    for g in gate_entries:
        name = g.get("name", "?")
        status = g.get("status", "?")
        summary.append({"name": name, "status": status})
        if status != "pass" and first_fail is None:
            first_fail = name
    return summary, first_fail


def _summarize_manifest(manifest_path: Path) -> Dict[str, Any]:
    data = _load_json(manifest_path) or {}
    files = data.get("files", []) or []
    return {
        "fingerprint": data.get("fingerprint_sha256"),
        "file_count": len(files),
    }


def _summarize_schema(schema_path: Path) -> Dict[str, Any]:
    data = _load_json(schema_path) or {}
    errs = data.get("errors", [])
    if isinstance(errs, list):
        count = len(errs)
    elif isinstance(errs, int):
        count = errs
    else:
        count = 0
    return {"errors": count}


def _summarize_bench(bench_path: Path) -> Dict[str, Any]:
    data = _load_json(bench_path) or {}
    acc = data.get("accuracy", {}) if isinstance(data, dict) else {}
    return {
        "pass_rate": data.get("cases_succeeded"),
        "cases_total": data.get("cases_total"),
        "f1": acc.get("f1"),
        "p95_latency_ms": data.get("p95_latency_ms"),
    }


def _summarize_replay(replay_path: Path) -> Dict[str, Any]:
    data = _load_json(replay_path) or {}
    if not data:
        return {}
    return {
        "run_a": data.get("run_a"),
        "run_b": data.get("run_b"),
        "fingerprint_equal": data.get("fingerprint_equal"),
    }


def diagnose(run_id: str, run_dir: Path, artifacts_root: Path) -> Tuple[str, List[str]]:
    lines: List[str] = []
    exit_fail = False

    lines.append(f"Run: {run_id}")

    gates_summary, first_fail = _summarize_gates(run_dir / EVIDENCE_FILES["gates"])
    if gates_summary:
        statuses = ", ".join(f"{g['name']}:{g['status']}" for g in gates_summary)
        lines.append(f"Gates: {statuses}")
        if first_fail:
            exit_fail = True
    else:
        lines.append("Gates: (not found)")

    meta = _load_json(run_dir / EVIDENCE_FILES["run_metadata"]) or {}
    if meta:
        lines.append(f"Failure category: {meta.get('failure_category', 'unknown')}")
        if meta.get("final_status") == "failed":
            exit_fail = True

    manifest_info = _summarize_manifest(run_dir / EVIDENCE_FILES["manifest"])
    if manifest_info.get("fingerprint"):
        lines.append(
            f"Manifest: fingerprint={manifest_info['fingerprint']} files={manifest_info['file_count']}"
        )

    schema_info = _summarize_schema(run_dir / EVIDENCE_FILES["schema_report"])
    if schema_info:
        lines.append(f"Schema errors: {schema_info['errors']}")
        if schema_info["errors"]:
            exit_fail = True

    bench_path = (run_dir / EVIDENCE_FILES["bench"]).resolve()
    if bench_path.exists():
        bench_info = _summarize_bench(bench_path)
        lines.append(
            f"Bench: pass_rate={bench_info.get('pass_rate')}/{bench_info.get('cases_total')} f1={bench_info.get('f1')} p95ms={bench_info.get('p95_latency_ms')}"
        )

    replay_path = (artifacts_root / "replay" / "report.json")
    if replay_path.exists():
        replay_info = _summarize_replay(replay_path)
        if replay_info:
            lines.append(
                f"Replay: runs {replay_info.get('run_a')} vs {replay_info.get('run_b')} fingerprint_equal={replay_info.get('fingerprint_equal')}"
            )
            if replay_info.get("fingerprint_equal") is False:
                exit_fail = True

    pointers = []
    for key, rel in EVIDENCE_FILES.items():
        path = (run_dir / rel).resolve() if not rel.startswith("../") else (run_dir / rel).resolve()
        if path.exists():
            pointers.append(str(path))
    lines.append("Evidence files:")
    lines.extend(f"- {p}" for p in sorted(set(pointers)))

    return ("\n".join(lines), ["fail"] if exit_fail else [])


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose a run using evidence artifacts.")
    parser.add_argument("--run-id")
    parser.add_argument("--artifacts-dir", help="Artifacts root (default ./artifacts)")
    args = parser.parse_args()

    artifacts_root = _artifacts_root(args.artifacts_dir)
    run_id, run_dir = _resolve_run_id(args.run_id, artifacts_root)

    output, failures = diagnose(run_id, run_dir, artifacts_root)
    print(output)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
