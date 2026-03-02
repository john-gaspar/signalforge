from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict


def _artifacts_root(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    return Path(os.getenv("ARTIFACTS_DIR", "artifacts"))


def _baseline_dir(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    return Path(__file__).resolve().parents[1] / "baselines" / "evidence"


def _bench_baseline_path(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    return Path(__file__).resolve().parents[1] / "baselines" / "bench_baseline.json"


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def _discover_run_id(run_id_arg: str | None, artifacts_root: Path) -> str:
    if run_id_arg:
        return run_id_arg
    hint = artifacts_root / "latest_seed_run_id"
    if hint.exists():
        return hint.read_text().strip()
    raise RuntimeError("Missing run_id; provide --run-id or ensure artifacts/latest_seed_run_id exists.")


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _sanitize_run_id(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload)
    data["run_id"] = "baseline"
    return data


def _regen_evidence_baseline(run_id: str, artifacts_root: Path, baseline_dir: Path) -> None:
    run_dir = artifacts_root / "runs" / run_id
    manifest_src = run_dir / "manifest.json"
    schema_src = run_dir / "schema_report.json"
    bench_src = artifacts_root / "bench" / "latest.json"
    if not manifest_src.exists() or not schema_src.exists() or not bench_src.exists():
        missing = [str(p) for p in [manifest_src, schema_src, bench_src] if not p.exists()]
        raise RuntimeError(f"Missing required evidence sources: {', '.join(missing)}")

    manifest = _sanitize_run_id(_load_json(manifest_src))
    schema = _sanitize_run_id(_load_json(schema_src))
    bench = _load_json(bench_src)
    bench_payload = {
        "run_id": "baseline",
        "cases_succeeded": bench.get("cases_succeeded"),
        "cases_total": bench.get("cases_total"),
        "p95_latency_ms": bench.get("p95_latency_ms"),
        "accuracy": {"f1": bench.get("accuracy", {}).get("f1") if isinstance(bench.get("accuracy"), dict) else None},
    }

    _write_json(baseline_dir / "manifest.json", manifest)
    _write_json(baseline_dir / "schema_report.json", schema)
    _write_json(baseline_dir / "bench_expected.json", bench_payload)


def _maybe_update_bench_baseline(bench_result: Path, bench_baseline_path: Path, enabled: bool) -> None:
    if not enabled:
        return
    data = _load_json(bench_result)
    cases_total = data.get("cases_total") or 0
    pass_rate = (data.get("cases_succeeded") or 0) / max(cases_total, 1)
    p95 = data.get("p95_latency_ms")
    f1 = None
    acc = data.get("accuracy")
    if isinstance(acc, dict):
        f1 = acc.get("f1")

    payload = {
        "min_pass_rate": pass_rate,
        "max_p95_latency_ms": p95,
        "min_f1": f1,
    }
    _write_json(bench_baseline_path, payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate evidence and (optionally) bench baselines from latest run artifacts.")
    parser.add_argument("--run-id", help="Run id (default: artifacts/latest_seed_run_id)")
    parser.add_argument("--artifacts-dir", help="Artifacts root (default ./artifacts)")
    parser.add_argument("--baseline-dir", help="Evidence baseline directory (default sentinelqa/baselines/evidence)")
    parser.add_argument("--bench-baseline-path", help="Bench baseline path (default sentinelqa/baselines/bench_baseline.json)")
    parser.add_argument("--update-bench-baseline", action="store_true", help="Update bench baseline from latest bench result")
    args = parser.parse_args()

    artifacts_root = _artifacts_root(args.artifacts_dir)
    baseline_dir = _baseline_dir(args.baseline_dir)
    bench_baseline_path = _bench_baseline_path(args.bench_baseline_path)

    try:
        run_id = _discover_run_id(args.run_id, artifacts_root)
        bench_result = artifacts_root / "bench" / "latest.json"
        _regen_evidence_baseline(run_id, artifacts_root, baseline_dir)
        _maybe_update_bench_baseline(bench_result, bench_baseline_path, args.update_bench_baseline)
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] regenerate baselines: {exc}")
        sys.exit(1)

    print("[OK] regenerated evidence baseline bundle")
    if args.update_bench_baseline:
        print(f"[OK] updated bench baseline at {bench_baseline_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
