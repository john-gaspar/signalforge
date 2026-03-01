from __future__ import annotations

import argparse
import socket
import sys
import time


def wait_tcp(host: str, port: int, timeout: int = 60, interval: float = 1.0) -> None:
    """Poll a TCP host:port until it accepts a connection or timeout.

    Args:
        host: Target hostname or IP.
        port: Target port.
        timeout: Total seconds to wait before failing.
        interval: Seconds between attempts (capped by remaining time).
    """

    start = time.time()
    deadline = start + timeout
    next_log = 5
    last_error: Exception | None = None

    while True:
        try:
            with socket.create_connection((host, port), timeout=interval):
                return
        except Exception as exc:  # noqa: BLE001 - want to capture any socket error
            last_error = exc

        now = time.time()
        elapsed = now - start
        if elapsed >= timeout:
            raise RuntimeError(f"{host}:{port} not reachable after {int(elapsed)}s (last error: {last_error})")

        if elapsed >= next_log:
            print(f"Waiting for {host}:{port} (elapsed {int(elapsed)}s) ...")
            next_log += 5

        remaining = max(0.0, deadline - now)
        sleep_for = min(interval, remaining)
        time.sleep(sleep_for if sleep_for > 0 else 0.01)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    try:
        wait_tcp(args.host, args.port, args.timeout)
        print(f"{args.host}:{args.port} is reachable")
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
