from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Iterable, List

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
THRESHOLDS_PATH = REPO_ROOT / "sentinelqa" / "gates" / "thresholds.yaml"
DEFAULT_TREND_CFG = {
    "window": 10,
    "min_history": 5,
    "max_negative_f1_slope": -0.001,
    "max_negative_pass_slope": -0.001,
    "max_positive_latency_slope": 1.0,
}


def _load_thresholds() -> dict:
    data = yaml.safe_load(THRESHOLDS_PATH.read_text()) or {}
    return {**DEFAULT_TREND_CFG, **(data.get("trend") or {})}


def _load_history(history_path: Path, window: int) -> List[dict]:
    if not history_path.exists():
        return []

    entries: List[dict] = []
    with history_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"[trend] invalid json in history: {exc}") from exc
    return entries[-window:]


def _slope(values: Iterable[float]) -> float:
    vals = list(values)
    n = len(vals)
    if n < 2:
        return 0.0
    x = list(range(n))
    sum_x = sum(x)
    sum_y = sum(vals)
    sum_xy = sum(i * y for i, y in zip(x, vals))
    sum_x2 = sum(i * i for i in x)
    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        return 0.0
    return (n * sum_xy - sum_x * sum_y) / denom


def main() -> None:
    artifacts_root = Path(os.getenv("ARTIFACTS_DIR", "artifacts"))
    history_path = artifacts_root / "bench" / "history.jsonl"
    cfg = _load_thresholds()

    history = _load_history(history_path, int(cfg["window"]))
    if len(history) < int(cfg["min_history"]):
        print(f"[trend] skip: only {len(history)} history entries (need {cfg['min_history']})")
        sys.exit(0)

    try:
        f1_values = [float(e["f1"]) for e in history]
        pass_rates = [float(e["pass_rate"]) for e in history]
        latencies = [float(e["p95_latency_ms"]) for e in history]
    except KeyError as exc:
        raise SystemExit(f"[trend] missing key in history: {exc}") from exc

    f1_slope = _slope(f1_values)
    pass_slope = _slope(pass_rates)
    lat_slope = _slope(latencies)

    failures = []
    if f1_slope < cfg["max_negative_f1_slope"]:
        failures.append(f"f1 slope {f1_slope:.4f} < {cfg['max_negative_f1_slope']}")
    if pass_slope < cfg["max_negative_pass_slope"]:
        failures.append(f"pass_rate slope {pass_slope:.4f} < {cfg['max_negative_pass_slope']}")
    if lat_slope > cfg["max_positive_latency_slope"]:
        failures.append(f"p95_latency_ms slope {lat_slope:.4f} > {cfg['max_positive_latency_slope']}")

    if failures:
        print("TREND REGRESSION GATE FAIL")
        for msg in failures:
            print(f"- {msg}")
        sys.exit(1)

    print("TREND REGRESSION GATE PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
