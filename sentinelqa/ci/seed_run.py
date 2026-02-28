from __future__ import annotations

import argparse
import json
import os
import sys
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


def _resolve_base_url(cli_base: str | None) -> str:
    if cli_base:
        return cli_base

    env_base = os.getenv("SEED_BASE_URL")
    if env_base:
        return env_base

    running_in_docker = (
        os.getenv("RUNNING_IN_DOCKER") == "1"
        or Path("/.dockerenv").exists()
        or Path("/code").exists()
    )
    if running_in_docker:
        return "http://api:8000"
    return "http://localhost:8000"


def _wait_api_ready(base_url: str, timeout: int = 60) -> None:
    parsed = urlparse(base_url)
    host = parsed.hostname or "localhost"
    use_curl_only = host in {"localhost", "127.0.0.1"}
    last_error = None
    deadline = time.time() + timeout
    while time.time() < deadline:
        if use_curl_only:
            result = subprocess.run(
                ["curl", "--ipv4", "--noproxy", "*", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"{base_url}/health"],
                capture_output=True,
            )
            if result.returncode == 0 and result.stdout.startswith(b"2"):
                return
            last_error = result.stderr.decode() or result.stdout.decode()
            time.sleep(1)
            continue
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=2):
                return
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", None)
            perm = isinstance(reason, PermissionError) or (isinstance(reason, OSError) and getattr(reason, "errno", None) == 1)
            if perm:
                last_error = exc
                result = subprocess.run(
                    ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"{base_url}/health"],
                    capture_output=True,
                )
                if result.returncode == 0 and result.stdout.startswith(b"2"):
                    return
            else:
                last_error = exc
            time.sleep(1)
        except Exception as exc:
            last_error = exc
            time.sleep(1)
    sys.exit(f"API not reachable/healthy after {timeout}s: {last_error}")


def _post_run(base_url: str, payload: dict, timeout: int = 60) -> str:
    data = json.dumps(payload).encode()
    parsed = urlparse(base_url)
    host = parsed.hostname or "localhost"
    use_curl_only = host in {"localhost", "127.0.0.1"}
    deadline = time.time() + timeout
    while time.time() < deadline:
        if use_curl_only:
            result = subprocess.run(
                [
                    "curl",
                    "--ipv4",
                    "--noproxy",
                    "*",
                    "-s",
                    "-H",
                    "Content-Type: application/json",
                    "-d",
                    json.dumps(payload),
                    f"{base_url}/runs/replay",
                ],
                capture_output=True,
            )
            if result.returncode == 0:
                try:
                    body = json.loads(result.stdout.decode())
                    run_id = body.get("run_id")
                    if run_id:
                        return run_id
                except Exception:
                    print(f"Unexpected curl response: {result.stdout}")
            else:
                print(f"curl POST failed: {result.stderr.decode()}")
            time.sleep(1)
            continue
        try:
            req = urllib.request.Request(
                f"{base_url}/runs/replay",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                body = json.load(resp)
                run_id = body.get("run_id")
                if run_id:
                    return run_id
                else:
                    print(f"Unexpected response payload: {body}")
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", None)
            perm = isinstance(reason, PermissionError) or (isinstance(reason, OSError) and getattr(reason, "errno", None) == 1)
            if perm:
                result = subprocess.run(
                    [
                        "curl",
                        "--ipv4",
                        "--noproxy",
                        "*",
                        "-s",
                        "-H",
                        "Content-Type: application/json",
                        "-d",
                        json.dumps(payload),
                        f"{base_url}/runs/replay",
                    ],
                    capture_output=True,
                )
                if result.returncode == 0:
                    try:
                        body = json.loads(result.stdout.decode())
                        run_id = body.get("run_id")
                        if run_id:
                            return run_id
                    except Exception:
                        print(f"Unexpected curl response: {result.stdout}")
                else:
                    print(f"curl POST failed: {result.stderr.decode()}")
            else:
                print(f"POST /runs/replay failed: {exc}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode() if hasattr(exc, "read") else str(exc)
            print(f"POST /runs/replay failed: HTTP {exc.code} {detail}")
        except Exception as exc:
            print(f"POST /runs/replay failed: {exc}")
            time.sleep(1)
    sys.exit("Failed to create seed run via API within timeout")


def _wait_run(base_url: str, run_id: str, timeout: int = 60) -> str:
    deadline = time.time() + timeout
    last_status = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/runs/{run_id}", timeout=2) as resp:
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", help="Base URL for API (default auto-detected)")
    args = parser.parse_args()

    base_url = _resolve_base_url(args.base_url)
    print(f"Seed run using base URL: {base_url}")

    _wait_api_ready(base_url)
    run_id = _post_run(base_url, {"fixtures_dir": "fixtures/tickets", "fault_config": {}})
    print(f"Seed run created: {run_id}")
    status = _wait_run(base_url, run_id)
    print(f"Seed run {run_id} completed with status {status}")


if __name__ == "__main__":
    main()
