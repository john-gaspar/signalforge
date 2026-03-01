from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List


def generate_report(raw_path: Path, out_path: Path) -> dict:
    raw = json.loads(raw_path.read_text())
    duration_s = float(raw.get("duration_s", 0))
    runs_done = int(raw.get("runs_succeeded", 0))
    throughput_rpm = (runs_done / duration_s * 60) if duration_s else 0.0

    report = {
        "requests_total": raw.get("requests_total", 0),
        "requests_failed": raw.get("requests_failed", 0),
        "success_rate": raw.get("success_rate", 0.0),
        "enqueue_latency_ms_p50": raw.get("enqueue_latency_ms_p50", 0),
        "enqueue_latency_ms_p95": raw.get("enqueue_latency_ms_p95", 0),
        "completion_time_s_p50": raw.get("completion_time_s_p50", 0.0),
        "completion_time_s_p95": raw.get("completion_time_s_p95", 0.0),
        "throughput_rpm": throughput_rpm,
        "duration_s": duration_s,
        "users": raw.get("users"),
        "spawn_rate": raw.get("spawn_rate"),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic load report")
    parser.add_argument("--raw", default="artifacts/load/raw.json", help="Path to raw metrics json")
    parser.add_argument("--out", default="artifacts/load/latest.json", help="Output report path")
    args = parser.parse_args(argv)

    raw_path = Path(args.raw)
    out_path = Path(args.out)
    if not raw_path.exists():
        raise SystemExit(f"raw metrics not found: {raw_path}")
    generate_report(raw_path, out_path)
    print(f"Wrote load report to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
