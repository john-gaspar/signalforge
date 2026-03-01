from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Tuple

from neo4j import Driver

from sentinelqa.graph.client import get_driver
from sentinelqa.graph.persist import load_artifacts, persist_to_graph, summarize_expected
from sentinelqa.graph.invariants import check_invariants


def _latest_run_dir() -> Tuple[Path | None, str | None]:
    hint = Path("artifacts/latest_seed_run_id")
    if hint.exists():
        run_id = hint.read_text().strip()
        run_dir = Path("artifacts/runs") / run_id
        if run_dir.exists():
            return run_dir, run_id

    artifacts_root = Path("artifacts/runs")
    metrics_files = sorted(
        artifacts_root.glob("**/metrics.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not metrics_files:
        return None, None
    metrics_path = metrics_files[0]
    return metrics_path.parent, metrics_path.parent.name


def _wait_neo4j(driver: Driver, timeout: int = 60) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            driver.verify_connectivity()
            return
        except Exception as exc:  # neo4j exceptions not always subclassed
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"Neo4j not ready after {timeout}s: {last_error}")


def main() -> None:
    run_dir, run_id = _latest_run_dir()
    if not run_dir or not run_id:
        sys.exit("No artifacts found under artifacts/runs")

    artifacts = load_artifacts(run_dir)
    expected = summarize_expected(artifacts)

    driver = get_driver()
    try:
        _wait_neo4j(driver)
        persist_to_graph(run_id, artifacts, driver)
        issues = check_invariants(driver, run_id, expected)
    finally:
        driver.close()

    if issues:
        print("[FAIL] graph invariants")
        for issue in issues:
            print(f" - {issue}")
        sys.exit(1)

    print("[PASS] graph invariants")
    sys.exit(0)


if __name__ == "__main__":
    main()
