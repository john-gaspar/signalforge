from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _load_json(path: Path) -> Dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _resolve_run_id(artifacts_root: Path) -> Tuple[str | None, Path | None]:
    hint = artifacts_root / "latest_seed_run_id"
    if not hint.exists():
        return None, None
    run_id = hint.read_text().strip()
    run_dir = artifacts_root / "runs" / run_id
    if not run_dir.exists():
        return run_id, None
    return run_id, run_dir


def _summarize_gates(gates_path: Path) -> Tuple[str, str | None]:
    data = _load_json(gates_path) or {}
    gates = data.get("gates") or []
    first_fail = None
    error_excerpt = None
    for g in gates:
        name = g.get("name", "?")
        status = g.get("status", "?")
        if status != "pass" and first_fail is None:
            first_fail = name
            err = g.get("error")
            if isinstance(err, str):
                error_excerpt = err[:160]
    if first_fail:
        return f"first_fail={first_fail}", error_excerpt
    if gates:
        return "all_pass", None
    return "missing", None


def _fmt(value: Any, label: str) -> str:
    if value is None:
        return f"{label}=?"
    return f"{label}={value}"


def diagnose(artifacts_dir: str | None = None) -> List[str]:
    artifacts_root = Path(artifacts_dir or "artifacts")

    run_id, run_dir = _resolve_run_id(artifacts_root)
    if run_id is None:
        return ["[diagnose] no seeded run id"]
    if run_dir is None:
        return [f"[diagnose] run artifacts missing for id {run_id}"]

    lines: List[str] = [f"[diagnose] run {run_id}"]

    gates_status, err_excerpt = _summarize_gates(run_dir / "gates.json")
    line = f"gates {gates_status}"
    if err_excerpt:
        line += f" error='{err_excerpt}'"
    lines.append(line)

    meta = _load_json(run_dir / "run_metadata.json") or {}
    failure_cat = meta.get("failure_category")
    duration = meta.get("run_duration_ms")
    if failure_cat or duration:
        parts = []
        if failure_cat:
            parts.append(f"category={failure_cat}")
        if duration is not None:
            parts.append(f"duration_ms={duration}")
        lines.append("metadata " + " ".join(parts))

    manifest = _load_json(run_dir / "manifest.json") or {}
    fp = manifest.get("fingerprint_sha256")
    if fp:
        lines.append(f"manifest fp={fp}")

    schema = _load_json(run_dir / "schema_report.json") or {}
    errs = schema.get("errors")
    if errs is not None:
        if isinstance(errs, list):
            errs = len(errs)
        lines.append(_fmt(errs, "schema_errors"))

    bench_path = artifacts_root / "bench" / "latest.json"
    if bench_path.exists():
        bench_data = _load_json(bench_path) or {}
        total = bench_data.get("cases_total") or 0
        succ = bench_data.get("cases_succeeded") or 0
        pass_rate = succ / total if total else None
        acc = bench_data.get("accuracy") or {}
        f1 = acc.get("f1") if isinstance(acc, dict) else None
        p95 = bench_data.get("p95_latency_ms")
        bench_line = "bench " + " ".join(
            [
                _fmt(pass_rate, "pass_rate"),
                _fmt(f1, "f1"),
                _fmt(p95, "p95ms"),
            ]
        )
        lines.append(bench_line)

    evidence_diff = run_dir / "evidence_diff.json"
    if evidence_diff.exists():
        data = _load_json(evidence_diff) or {}
        manifest_diff = data.get("manifest") or {}
        changed = (manifest_diff.get("changed") or []) + (manifest_diff.get("added") or []) + (
            manifest_diff.get("removed") or []
        )
        lines.append(f"evidence_diff changed_files={len(changed)}")

    return lines


def main() -> None:
    lines = diagnose()
    for line in lines:
        print(line)


if __name__ == "__main__":
    main()
