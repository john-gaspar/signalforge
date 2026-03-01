from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Tuple

from sentinelqa.artifacts.manifest import validate_manifest


def _latest_run_dir(artifacts_root: Path) -> Tuple[Path | None, str | None]:
    hint = Path("artifacts/latest_seed_run_id")
    if hint.exists():
        run_id = hint.read_text().strip()
        run_dir = artifacts_root / run_id
        if run_dir.exists():
            return run_dir, run_id

    metrics_files = sorted(
        artifacts_root.glob("**/metrics.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not metrics_files:
        return None, None
    metrics_path = metrics_files[0]
    return metrics_path.parent, metrics_path.parent.name


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify per-run artifact manifest integrity")
    parser.add_argument("--artifacts-root", default="artifacts/runs")
    args = parser.parse_args()

    artifacts_root = Path(args.artifacts_root)
    run_dir, run_id = _latest_run_dir(artifacts_root)
    if not run_dir or not run_id:
        sys.exit("No run artifacts found; cannot verify manifest")

    manifest_path = run_dir / "manifest.json"
    errors = validate_manifest(manifest_path)
    if errors:
        print("[FAIL] manifest integrity")
        for err in errors:
            print(f" - {err}")
        sys.exit(1)

    files = (manifest_path.parent / "manifest.json").read_text()
    print(f"[OK] manifest integrity for {run_id}")
    print(f" path={manifest_path} entries_verified")
    sys.exit(0)


if __name__ == "__main__":
    main()
