from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.request


def wait_http(url: str, timeout: int = 60) -> None:
    start = time.time()
    next_log = 5
    last_error: str | Exception | None = None

    while True:
        elapsed = time.time() - start
        if elapsed > timeout:
            raise RuntimeError(f"{url} not ready after {int(elapsed)}s (last error: {last_error})")

        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if 200 <= resp.status < 300:
                    return
                last_error = f"HTTP {resp.status}"
        except (urllib.error.URLError, ConnectionRefusedError, TimeoutError, Exception) as exc:
            last_error = exc

        if elapsed >= next_log:
            print(f"Waiting for {url} (elapsed {int(elapsed)}s) ...")
            next_log += 5

        time.sleep(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    try:
        wait_http(args.url, args.timeout)
        print(f"{args.url} is ready")
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
