from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Sequence

TARGET_PREFIXES = (
    "sentinelqa/baselines/",
    "sentinelqa/schemas/",
    "sentinelqa/contracts/",
)


def _run_git(args: Sequence[str]) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _merge_base() -> str | None:
    event = os.getenv("GITHUB_EVENT_NAME", "")
    if event == "pull_request":
        base_ref = os.getenv("GITHUB_BASE_REF")
        if not base_ref:
            raise RuntimeError("GITHUB_BASE_REF is required for pull_request event")
        # Ensure we diff against the base branch ref (fetched by checkout)
        return _run_git(["merge-base", "HEAD", f"origin/{base_ref}"])

    # push / workflow_dispatch / others: use previous commit when available
    try:
        _run_git(["rev-parse", "HEAD~1"])
        return "HEAD~1"
    except subprocess.CalledProcessError:
        # First commit or shallow clone
        return None


def _changed_files(base: str | None) -> List[str]:
    args = ["diff", "--name-only"]
    if base:
        args.extend([base, "HEAD"])
    else:
        # No base means just report working tree changes (e.g., first commit)
        args.append("HEAD")
    try:
        output = _run_git(args)
    except subprocess.CalledProcessError as exc:  # type: ignore[misc]
        raise RuntimeError(f"git diff failed: {exc.stderr}") from exc  # noqa: B904
    return [line.strip() for line in output.splitlines() if line.strip()]


def _matches_targets(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in TARGET_PREFIXES)


def main() -> None:
    try:
        base = _merge_base()
        files = _changed_files(base)
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] baseline guard: {exc}")
        sys.exit(1)

    flagged = [f for f in files if _matches_targets(f)]
    if not flagged:
        print("[OK] baseline guard: no baseline/schema/contract changes detected")
        sys.exit(0)

    if os.getenv("BASELINE_UPDATE") == "1":
        print("[OK] baseline guard: changes allowed (BASELINE_UPDATE=1)")
        for f in flagged:
            print(f" - {f}")
        sys.exit(0)

    print("[FAIL] baseline guard: blocked changes to baselines/schemas/contracts")
    for f in flagged:
        print(f" - {f}")
    print("Set BASELINE_UPDATE=1 to allow intentional updates or use the manual Update Baselines workflow.")
    sys.exit(1)


if __name__ == "__main__":
    main()
