from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx


def post_replay(base_url: str, fixtures_dir: str) -> str:
    resp = httpx.post(
        f"{base_url}/runs/replay",
        json={"fixtures_dir": fixtures_dir, "fault_config": {}},
        timeout=10,
    )
    resp.raise_for_status()
    run_id = resp.json().get("run_id")
    if not run_id:
        raise RuntimeError("run_id missing in replay response")
    return run_id


def poll_run(base_url: str, run_id: str, timeout: int = 60) -> dict:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        resp = httpx.get(f"{base_url}/runs/{run_id}", timeout=5)
        if resp.status_code == 200:
            body = resp.json()
            status = body.get("status")
            last = body
            if status == "succeeded":
                return body
            if status == "failed":
                raise RuntimeError(f"run {run_id} failed: {body.get('error')}")
        time.sleep(1)
    raise RuntimeError(f"run {run_id} did not complete in time; last={last}")


def load_artifacts(artifacts_dir: Path, run_id: str) -> tuple[list[dict], dict]:
    run_dir = artifacts_dir / "runs" / run_id
    events = json.loads((run_dir / "events.json").read_text())
    metrics = json.loads((run_dir / "metrics.json").read_text())
    return events, metrics


def compute_summary(events: list[dict], metrics: dict) -> dict:
    lat = metrics.get("latency_ms", 0)
    return {
        "cases_total": len(events),
        "cases_succeeded": len(events),
        "p50_latency_ms": lat,
        "p95_latency_ms": lat,
    }


def evaluate(expectations: dict, events: list[dict], metrics: dict) -> list[str]:
    errors = []
    if len(events) < expectations.get("min_events", 0):
        errors.append(f"events {len(events)} < min_events")
    if metrics.get("clusters", 0) < expectations.get("min_clusters", 0):
        errors.append(f"clusters {metrics.get('clusters')} < min_clusters")
    for key in expectations.get("required_keys", []):
        if key not in metrics:
            errors.append(f"metrics missing key {key}")
    return errors


def run_benchmark(base_url: str, fixtures: Path, out_path: Path) -> dict:
    base_url = base_url.rstrip("/")
    run_id = post_replay(base_url, str(fixtures))
    poll_run(base_url, run_id, timeout=120)

    artifacts_dir = Path(os.getenv("ARTIFACTS_DIR", "artifacts"))
    events, metrics = load_artifacts(artifacts_dir, run_id)
    expectations = json.loads((fixtures / "expectations.json").read_text())

    summary = compute_summary(events, metrics)
    summary["run_id"] = run_id
    summary["errors"] = evaluate(expectations, events, metrics)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--fixtures", default="fixtures/golden")
    parser.add_argument("--out", default="artifacts/bench/latest.json")
    args = parser.parse_args()

    summary = run_benchmark(args.base_url, Path(args.fixtures), Path(args.out))
    print(json.dumps(summary, indent=2))
    if summary["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
