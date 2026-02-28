from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request


def wait_http(url: str, timeout: int = 60) -> None:
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if 200 <= resp.status < 300:
                    return
        except urllib.error.URLError as exc:
            last_error = exc
            # fallback to curl when permission errors occur
            result = subprocess.run(
                ["curl", "--ipv4", "--noproxy", "*", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
                capture_output=True,
            )
            if result.returncode == 0 and result.stdout.startswith(b"2"):
                return
            last_error = result.stdout.decode()
        except Exception as exc:
            last_error = exc
        time.sleep(1)
    sys.exit(f"wait_http: {url} not ready after {timeout}s (last error: {last_error})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    wait_http(args.url, args.timeout)
    print(f"{args.url} is ready")


if __name__ == "__main__":
    main()
