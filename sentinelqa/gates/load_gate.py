from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _fail(msg: str):
    print("[FAIL] load gate")
    print(f" - {msg}")
    sys.exit(1)


def _check_threshold(name: str, value: float, op: str, limit: float, details: list[str]):
    if op == "min" and value < limit:
        details.append(f"{name}: {value:.3f} < min {limit}")
    if op == "max" and value > limit:
        details.append(f"{name}: {value:.3f} > max {limit}")


def main() -> None:
    report_path = Path(os.getenv("LOAD_REPORT_PATH", "artifacts/load/latest.json"))
    baseline_path = Path(os.getenv("LOAD_BASELINE_PATH", "sentinelqa/baselines/load_baseline.json"))

    if not report_path.exists():
        _fail(f"report missing at {report_path}")
    if not baseline_path.exists():
        _fail(f"baseline missing at {baseline_path}")

    report = _load_json(report_path)
    baseline = _load_json(baseline_path)

    details: list[str] = []
    _check_threshold(
        "success_rate",
        float(report.get("success_rate", 0.0)),
        "min",
        float(baseline.get("min_success_rate", 0.0)),
        details,
    )
    _check_threshold(
        "enqueue_latency_ms_p95",
        float(report.get("enqueue_latency_ms_p95", 0.0)),
        "max",
        float(baseline.get("max_enqueue_latency_ms_p95", 1e9)),
        details,
    )
    _check_threshold(
        "completion_time_s_p95",
        float(report.get("completion_time_s_p95", 0.0)),
        "max",
        float(baseline.get("max_completion_time_s_p95", 1e9)),
        details,
    )
    _check_threshold(
        "throughput_rpm",
        float(report.get("throughput_rpm", 0.0)),
        "min",
        float(baseline.get("min_throughput_rpm", 0.0)),
        details,
    )

    if details:
        _fail("; ".join(details))

    print("[PASS] load gate")
    print(
        f" success_rate={report.get('success_rate'):.3f}, "
        f"p95_enqueue_ms={report.get('enqueue_latency_ms_p95')}, "
        f"p95_completion_s={report.get('completion_time_s_p95')}, "
        f"throughput_rpm={report.get('throughput_rpm'):.2f}"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
