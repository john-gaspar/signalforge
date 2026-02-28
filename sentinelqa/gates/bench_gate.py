from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from sentinelqa.bench.run import run_benchmark


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def compare(baseline: dict, current: dict) -> list[str]:
    errors = []
    pass_rate = current["cases_succeeded"] / max(current["cases_total"], 1)
    if pass_rate < baseline.get("min_pass_rate", 1.0):
        errors.append(
            f"pass_rate current={pass_rate:.2f} baseline>={baseline['min_pass_rate']:.2f}"
        )

    cur_p95 = current.get("p95_latency_ms", 0)
    max_p95 = baseline.get("max_p95_latency_ms")
    if max_p95 is not None and cur_p95 > max_p95:
        errors.append(f"p95_latency_ms current={cur_p95} baseline<={max_p95}")
    return errors


def main() -> None:
    root = repo_root()
    baseline_path = Path(os.environ.get("BENCH_BASELINE_PATH", root / "sentinelqa/baselines/bench_baseline.json"))
    result_path = Path(os.environ.get("BENCH_RESULT_PATH", root / "artifacts/bench/latest.json"))
    fixtures_path = Path(os.environ.get("BENCH_FIXTURES", root / "fixtures/golden"))
    base_url = os.environ.get("BENCH_BASE_URL", "http://api:8000")

    if not result_path.exists():
        summary = run_benchmark(base_url, fixtures_path, result_path)
        print(json.dumps(summary, indent=2))

    baseline = load_json(baseline_path)
    current = load_json(result_path)

    errors = compare(baseline, current)
    if errors:
        print("BENCHMARK GATE FAILED")
        for e in errors:
            print(f"- {e}")
        sys.exit(1)

    print("BENCHMARK GATE PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
