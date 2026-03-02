from __future__ import annotations

import os
import subprocess
import sys
from typing import Iterable, List, Sequence, Tuple

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


def _changed_files(base: str | None) -> List[Tuple[str, str]]:
    args = ["diff", "--name-status"]
    if base:
        args.extend([base, "HEAD"])
    else:
        # No base means just report working tree changes (e.g., first commit)
        args.append("HEAD")
    try:
        output = _run_git(args)
    except subprocess.CalledProcessError as exc:  # type: ignore[misc]
        raise RuntimeError(f"git diff failed: {exc.stderr}") from exc  # noqa: B904
    changes: List[Tuple[str, str]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        status, path = parts
        changes.append((status, path.strip()))
    return changes


def _matches_targets(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in TARGET_PREFIXES)


def evaluate_changed_paths(changed_paths: Iterable[Tuple[str, str]], allow: bool) -> Tuple[bool, List[str]]:
    changes = [(s, p) for s, p in changed_paths if p]

    if allow:
        flagged = [(s, p) for s, p in changes if _matches_targets(p)]
        if not flagged:
            return True, ["[OK] baseline guard: no protected changes detected"]
        lines = ["[OK] baseline guard: changes allowed (BASELINE_UPDATE=1)"]
        lines.extend(f" - {s} {p}" for s, p in flagged)
        return True, lines

    blocked: List[str] = []
    for status, path in changes:
        if not _matches_targets(path):
            continue
        is_schema = path.startswith("sentinelqa/schemas/")

        if status.upper().startswith("A"):
            if is_schema:
                # Allow new schema files without the flag
                continue
            blocked.append(f"added-not-allowed: {path}")
        elif status.upper().startswith("D"):
            blocked.append(f"deleted: {path}")
        else:  # modifications / renames
            blocked.append(f"modified: {path}")

    if not blocked:
        return True, ["[OK] baseline guard: no protected changes detected"]

    lines = ["[FAIL] baseline guard: blocked protected changes"]
    lines.extend(f" - {b}" for b in blocked)
    lines.append("Set BASELINE_UPDATE=1 to allow intentional updates or use the manual Update Baselines workflow.")
    return False, lines


def main() -> None:
    try:
        base = _merge_base()
        files = _changed_files(base)
        allow = os.getenv("BASELINE_UPDATE") == "1"
        ok, lines = evaluate_changed_paths(files, allow)
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] baseline guard: {exc}")
        sys.exit(1)

    for line in lines:
        print(line)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
