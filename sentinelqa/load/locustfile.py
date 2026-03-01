from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import List

from locust import HttpUser, task, between, events

BASE_URL = os.getenv("BASE_URL", "http://api:8000")
FIXTURES_DIR = os.getenv("LOAD_FIXTURES_DIR", "fixtures/tickets")
RUN_TIMEOUT_S = int(os.getenv("LOAD_RUN_TIMEOUT_S", "120"))
RAW_PATH = Path(os.getenv("LOAD_RAW_PATH", "artifacts/load/raw.json"))
USERS = int(os.getenv("LOAD_USERS", os.getenv("LOCUST_USERS", "5")))
SPAWN_RATE = float(os.getenv("LOAD_SPAWN_RATE", os.getenv("LOCUST_SPAWN_RATE", "1")))
DURATION_S = int(os.getenv("LOAD_DURATION_S", os.getenv("LOCUST_DURATION", "60")))

_completion_samples: List[float] = []
_run_counts = {"succeeded": 0, "failed": 0}


def _percentile(data: List[float], pct: float) -> float:
    if not data:
        return 0.0
    data_sorted = sorted(data)
    k = (len(data_sorted) - 1) * pct
    f = int(k)
    c = min(f + 1, len(data_sorted) - 1)
    if f == c:
        return data_sorted[f]
    return data_sorted[f] + (data_sorted[c] - data_sorted[f]) * (k - f)


class ReplayUser(HttpUser):
    wait_time = between(0.1, 0.2)

    @task
    def replay_once(self):
        start = time.perf_counter()
        resp = self.client.post(
            "/runs/replay",
            json={"fixtures_dir": FIXTURES_DIR, "fault_config": {}},
            name="POST /runs/replay",
            timeout=10,
        )
        if not resp.ok:
            return
        try:
            run_id = resp.json().get("run_id")
        except Exception:
            return
        if not run_id:
            return

        deadline = time.time() + RUN_TIMEOUT_S
        while time.time() < deadline:
            r2 = self.client.get(f"/runs/{run_id}", name="GET /runs/{run_id}", timeout=10)
            if r2.ok:
                try:
                    status = r2.json().get("status")
                except Exception:
                    status = None
                if status == "succeeded":
                    elapsed = time.perf_counter() - start
                    _completion_samples.append(elapsed)
                    _run_counts["succeeded"] += 1
                    return
                if status == "failed":
                    _run_counts["failed"] += 1
                    return
            time.sleep(1)
        _run_counts["failed"] += 1


@events.test_stop.add_listener
def on_test_stop(environment, **_kwargs):
    """
    Serialize stable raw metrics for report generation.
    """
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    stats = environment.runner.stats.total
    data = {
        "requests_total": stats.num_requests,
        "requests_failed": stats.num_failures,
        "success_rate": (stats.num_requests - stats.num_failures) / stats.num_requests
        if stats.num_requests
        else 0.0,
        "enqueue_latency_ms_p50": stats.get_response_time_percentile(0.50),
        "enqueue_latency_ms_p95": stats.get_response_time_percentile(0.95),
        "completion_time_s": _completion_samples,
        "completion_time_s_p50": _percentile(_completion_samples, 0.50),
        "completion_time_s_p95": _percentile(_completion_samples, 0.95),
        "runs_succeeded": _run_counts["succeeded"],
        "runs_failed": _run_counts["failed"],
        "duration_s": DURATION_S,
        "users": USERS,
        "spawn_rate": SPAWN_RATE,
    }
    RAW_PATH.write_text(json.dumps(data, indent=2))
