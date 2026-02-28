from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sentinelqa.dq.drift import compute_summary


def _load_template(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    # Fallback minimal template
    return {
        "version": 1,
        "name": "signalforge_drift_baseline",
        "checks": {},
    }


def _set_baseline(template: dict, summary: dict) -> dict:
    checks = template.get("checks", {})
    for field, rule in checks.items():
        parts = field.split(".")
        cur = summary
        for part in parts:
            if not isinstance(cur, dict) or part not in cur:
                cur = None
                break
            cur = cur[part]
        if cur is None:
            continue
        rule["baseline"] = cur
    template["checks"] = checks
    template["generated_from"] = {"run_id": summary.get("run_id"), "source": "drift_baseline.py"}
    return template


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate drift baseline from run artifacts.")
    parser.add_argument("--run-id", required=True, help="Run id under artifacts/runs/")
    parser.add_argument("--force", action="store_true", help="Overwrite existing baseline.")
    parser.add_argument(
        "--baseline-path",
        default="sentinelqa/baselines/drift_baseline.json",
        help="Path to baseline JSON to write.",
    )
    args = parser.parse_args(argv)

    run_dir = Path("artifacts/runs") / args.run_id
    if not run_dir.exists():
        sys.exit(f"Run artifacts not found at {run_dir}")

    baseline_path = Path(args.baseline_path)
    if baseline_path.exists() and not args.force:
        sys.exit(f"{baseline_path} exists; rerun with --force to overwrite.")

    summary = compute_summary(run_dir)
    summary["run_id"] = args.run_id
    template = _load_template(baseline_path)
    updated = _set_baseline(template, summary)

    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(json.dumps(updated, indent=2))
    print(f"Wrote drift baseline to {baseline_path} from run {args.run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
