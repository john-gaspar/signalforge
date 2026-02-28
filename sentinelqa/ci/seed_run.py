from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request


API_BASE = "http://localhost:8000"


def _wait_api_ready(timeout: int = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{API_BASE}/openapi.json", timeout=2):
                return
        except Exception:
            time.sleep(1)
    sys.exit("API not reachable after 60s")


def _post_run(payload: dict, timeout: int = 60) -> str:
    data = json.dumps(payload).encode()
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(
                f"{API_BASE}/runs/replay",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                body = json.load(resp)
                return body["run_id"]
        except Exception:
            time.sleep(1)
    sys.exit("Failed to create seed run via API within timeout")


def _wait_run(run_id: str, timeout: int = 60) -> str:
    deadline = time.time() + timeout
    last_status = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{API_BASE}/runs/{run_id}", timeout=2) as resp:
                data = json.load(resp)
            status = data.get("status")
            last_status = status
            if status == "succeeded":
                return status
            if status == "failed":
                sys.exit(f"Seed run {run_id} failed")
        except urllib.error.HTTPError as exc:
            last_status = f"HTTP {exc.code}"
        except Exception:
            pass
        time.sleep(1)
    sys.exit(f"Seed run {run_id} did not complete within timeout (last status: {last_status})")


def main() -> None:
    _wait_api_ready()
    run_id = _post_run({"fixtures_dir": "fixtures/tickets", "fault_config": {}})
    status = _wait_run(run_id)
    print(f"Seed run {run_id} completed with status {status}")


if __name__ == "__main__":
    main()
