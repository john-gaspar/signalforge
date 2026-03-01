from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "PROJECT_SNAPSHOT.md"
SHA_LINE_RE = re.compile(r"^-\s*SHA:\s*(.+)$")


def parse_snapshot_sha(path: Path = SNAPSHOT_PATH) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        m = SHA_LINE_RE.match(line.strip())
        if m:
            return m.group(1).strip()
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Ensure PROJECT_SNAPSHOT.md HEAD SHA matches expected")
    parser.add_argument("--expected", help="Expected SHA (optional; if provided, must match snapshot)")
    args = parser.parse_args()

    expected = args.expected

    actual = parse_snapshot_sha()
    if not actual:
        sys.exit("SHA line missing in PROJECT_SNAPSHOT.md")
    if "<to be filled" in actual:
        sys.exit("PROJECT_SNAPSHOT.md contains placeholder SHA")
    if not (len(actual) == 40 and all(c in "0123456789abcdef" for c in actual.lower())):
        sys.exit(f"PROJECT_SNAPSHOT.md SHA invalid: {actual}")

    if expected:
        if actual != expected:
            sys.exit(f"Snapshot SHA mismatch: expected {expected}, found {actual}")
        print(f"[OK] PROJECT_SNAPSHOT.md SHA matches {expected}")
    else:
        print(f"[OK] PROJECT_SNAPSHOT.md SHA present and well-formed")


if __name__ == "__main__":
    main()
