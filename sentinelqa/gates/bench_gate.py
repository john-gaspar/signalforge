from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from sentinelqa.bench.run import run_benchmark
from sentinelqa.ci.bench_history import append_bench_history


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

    cur_f1 = current.get("accuracy", {}).get("f1", 0.0)
    min_f1 = float(os.environ.get("BENCH_F1_MIN", baseline.get("min_f1", 0.0)))
    if cur_f1 < min_f1:
        errors.append(f"f1 current={cur_f1:.4f} baseline>={min_f1:.4f}")

    return errors


def main() -> None:
    root = repo_root()
    baseline_path = Path(os.environ.get("BENCH_BASELINE_PATH", root / "sentinelqa/baselines/bench_baseline.json"))
    result_path = Path(os.environ.get("BENCH_RESULT_PATH", root / "artifacts/bench/latest.json"))
    fixtures_path = Path(os.environ.get("BENCH_FIXTURES", root / "fixtures/golden"))
    base_url = os.environ.get("BENCH_BASE_URL", "http://api:8000")
    mode = os.environ.get("BENCH_MODE", "fail")

    if not result_path.exists():
        summary = run_benchmark(base_url, fixtures_path, result_path)
        print(json.dumps(summary, indent=2))

    baseline = load_json(baseline_path)
    current = load_json(result_path)

    artifacts_root = Path(os.getenv("ARTIFACTS_DIR", repo_root() / "artifacts"))
    history_path_env = os.getenv("BENCH_HISTORY_PATH")
    history_path = Path(history_path_env) if history_path_env else artifacts_root / "bench" / "history.jsonl"
    append_bench_history(result_path, history_path)

    errors = compare(baseline, current)
    if errors:
        status = "WARN" if mode == "warn" else "FAIL"
        print(f"BENCHMARK GATE {status}")
        for e in errors:
            print(f"- {e}")
        if mode == "fail":
            sys.exit(1)
        else:
            sys.exit(0)

    print("BENCHMARK GATE PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
