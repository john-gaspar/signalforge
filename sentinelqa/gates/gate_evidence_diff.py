from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

BASELINE_DIR = Path(__file__).resolve().parents[1] / "baselines" / "evidence"


def _resolve_artifacts_root(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    env_dir = os.getenv("ARTIFACTS_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(__file__).resolve().parents[2] / "artifacts"


def _resolve_baseline_dir(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    env_dir = os.getenv("EVIDENCE_BASELINE_DIR")
    if env_dir:
        return Path(env_dir)
    return BASELINE_DIR


def _resolve_run_id(run_id_arg: str | None, artifacts_root: Path) -> Tuple[str, Path]:
    if run_id_arg:
        run_id = run_id_arg
    else:
        hint = artifacts_root / "latest_seed_run_id"
        run_id = hint.read_text().strip() if hint.exists() else None
    if not run_id:
        sys.exit("[FAIL] evidence diff: missing run_id (provide --run-id or artifacts/latest_seed_run_id)")
    run_dir = artifacts_root / "runs" / run_id
    if not run_dir.exists():
        sys.exit(f"[FAIL] evidence diff: run artifacts not found at {run_dir}")
    return run_id, run_dir


def _load_json(path: Path) -> Dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            raise ValueError(f"{path} is not a JSON object")
        return data
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"failed to load {path}: {exc}") from exc


def _manifest_map(payload: Dict[str, Any]) -> Dict[str, str]:
    files = payload.get("files")
    if not isinstance(files, list):
        return {}
    mapping: Dict[str, str] = {}
    for entry in files:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        sha = entry.get("sha256")
        if isinstance(path, str) and isinstance(sha, str):
            mapping[path] = sha
    return mapping


def _diff_manifest(current_path: Path, baseline_path: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "status": "ok",
        "current_path": str(current_path),
        "baseline_path": str(baseline_path),
        "changed": [],
        "added": [],
        "removed": [],
        "fingerprint_changed": None,
    }
    current = _load_json(current_path)
    baseline = _load_json(baseline_path)
    if current is None:
        result["status"] = "current_missing"
        return result
    if baseline is None:
        result["status"] = "baseline_missing"
        return result

    cur_map = _manifest_map(current)
    base_map = _manifest_map(baseline)

    changed = sorted([p for p in cur_map.keys() & base_map.keys() if cur_map[p] != base_map[p]])
    added = sorted(cur_map.keys() - base_map.keys())
    removed = sorted(base_map.keys() - cur_map.keys())

    result.update(
        {
            "changed": changed,
            "added": added,
            "removed": removed,
            "fingerprint_changed": current.get("fingerprint_sha256") != baseline.get("fingerprint_sha256"),
        }
    )
    return result


def _schema_errors(payload: Dict[str, Any] | None) -> Tuple[int | None, str | None]:
    if payload is None:
        return None, None
    errs = payload.get("errors")
    if isinstance(errs, list):
        count = len(errs)
    elif isinstance(errs, int):
        count = errs
    else:
        count = 0
    version = payload.get("schema_version") or payload.get("version")
    version_str = str(version) if version is not None else None
    return count, version_str


def _diff_schema(current_path: Path, baseline_path: Path) -> Dict[str, Any]:
    current = _load_json(current_path)
    baseline = _load_json(baseline_path)
    cur_errs, cur_ver = _schema_errors(current)
    base_errs, base_ver = _schema_errors(baseline)
    return {
        "status": "ok" if current or baseline else "missing",
        "current_path": str(current_path),
        "baseline_path": str(baseline_path),
        "current_errors": cur_errs,
        "baseline_errors": base_errs,
        "delta_errors": (cur_errs - base_errs) if cur_errs is not None and base_errs is not None else None,
        "current_version": cur_ver,
        "baseline_version": base_ver,
    }


def _bench_metrics(payload: Dict[str, Any] | None) -> Dict[str, float | None]:
    if payload is None:
        return {"pass_rate": None, "f1": None, "p95_latency_ms": None}
    cases_total = payload.get("cases_total")
    cases_succeeded = payload.get("cases_succeeded")
    pass_rate = None
    if isinstance(cases_total, (int, float)) and cases_total:
        pass_rate = float(cases_succeeded or 0) / float(cases_total)
    f1 = None
    acc = payload.get("accuracy")
    if isinstance(acc, dict):
        f1_val = acc.get("f1")
        if isinstance(f1_val, (int, float)):
            f1 = float(f1_val)
    p95 = payload.get("p95_latency_ms")
    if not isinstance(p95, (int, float)):
        p95 = None
    return {"pass_rate": pass_rate, "f1": f1, "p95_latency_ms": p95}


def _diff_bench(current_path: Path, baseline_path: Path) -> Dict[str, Any]:
    current = _load_json(current_path)
    baseline = _load_json(baseline_path)
    cur = _bench_metrics(current)
    base = _bench_metrics(baseline)

    def delta(cur_val: float | None, base_val: float | None) -> float | None:
        if cur_val is None or base_val is None:
            return None
        return cur_val - base_val

    return {
        "status": "ok" if current or baseline else "missing",
        "current_path": str(current_path),
        "baseline_path": str(baseline_path),
        "current": cur,
        "baseline": base,
        "delta": {
            "pass_rate": delta(cur["pass_rate"], base["pass_rate"]),
            "f1": delta(cur["f1"], base["f1"]),
            "p95_latency_ms": delta(cur["p95_latency_ms"], base["p95_latency_ms"]),
        },
    }


def compute_diff(run_id: str, run_dir: Path, artifacts_root: Path, baseline_dir: Path) -> Dict[str, Any]:
    manifest_path = run_dir / "manifest.json"
    schema_path = run_dir / "schema_report.json"
    bench_path = artifacts_root / "bench" / "latest.json"
    if not bench_path.exists():
        # fall back to run-local bench if present
        candidate = run_dir / "bench_report.json"
        if candidate.exists():
            bench_path = candidate

    diff = {
        "version": 1,
        "run_id": run_id,
        "baseline_dir": str(baseline_dir),
        "manifest": _diff_manifest(manifest_path, baseline_dir / "manifest.json"),
        "schema": _diff_schema(schema_path, baseline_dir / "schema_report.json"),
        "bench": _diff_bench(bench_path, baseline_dir / "bench_expected.json"),
        "paths": {
            "run_dir": str(run_dir),
            "artifacts_root": str(artifacts_root),
        },
    }
    out_path = run_dir / "evidence_diff.json"
    out_path.write_text(json.dumps(diff, indent=2, sort_keys=True))
    return diff


def _fmt_list(items: List[str]) -> str:
    return ", ".join(items) if items else "none"


def _print_summary(diff: Dict[str, Any]) -> None:
    manifest = diff["manifest"]
    schema = diff["schema"]
    bench = diff["bench"]

    print(f"Run: {diff['run_id']}")
    if manifest["status"] == "ok":
        print(
            f"Manifest: changed={_fmt_list(manifest['changed'])} "
            f"added={_fmt_list(manifest['added'])} removed={_fmt_list(manifest['removed'])}"
        )
    else:
        print(f"Manifest: {manifest['status']}")

    if schema["status"] != "missing":
        print(
            "Schema: baseline_errors={0} current_errors={1} delta={2} version {3}->{4}".format(
                schema.get("baseline_errors"),
                schema.get("current_errors"),
                schema.get("delta_errors"),
                schema.get("baseline_version"),
                schema.get("current_version"),
            )
        )
    else:
        print("Schema: missing")

    delta = bench["delta"]
    print(
        "Bench: pass_rate={0} (Δ {1}) f1={2} (Δ {3}) p95ms={4} (Δ {5})".format(
            bench["current"]["pass_rate"],
            delta.get("pass_rate"),
            bench["current"]["f1"],
            delta.get("f1"),
            bench["current"]["p95_latency_ms"],
            delta.get("p95_latency_ms"),
        )
    )
    print(f"Evidence diff written to: {diff['paths']['run_dir']}/evidence_diff.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare run evidence with baseline bundle")
    parser.add_argument("--run-id", help="Run id (optional; defaults to artifacts/latest_seed_run_id)")
    parser.add_argument("--artifacts-dir", help="Artifacts root (default ./artifacts)")
    parser.add_argument("--baseline-dir", help="Override evidence baseline directory")
    args = parser.parse_args()

    artifacts_root = _resolve_artifacts_root(args.artifacts_dir)
    baseline_dir = _resolve_baseline_dir(args.baseline_dir)
    try:
        run_id, run_dir = _resolve_run_id(args.run_id, artifacts_root)
        diff = compute_diff(run_id, run_dir, artifacts_root, baseline_dir)
        _print_summary(diff)
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] evidence diff: {exc}")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
