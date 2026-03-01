import json
import sys
from pathlib import Path

import pytest

from sentinelqa.cli import diagnose


def _write_run(tmp_path: Path, run_id: str, failing: bool = False) -> Path:
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "gates.json").write_text(
        json.dumps({"gates": [{"name": "graph", "status": "pass"}, {"name": "dq", "status": "fail" if failing else "pass"}]})
    )
    (run_dir / "run_metadata.json").write_text(
        json.dumps({"run_id": run_id, "final_status": "failed" if failing else "succeeded", "failure_category": "data_quality"})
    )
    (run_dir / "manifest.json").write_text(json.dumps({"fingerprint_sha256": "abc", "files": [{"path": "events.json", "sha256": "x", "bytes": 1}]}))
    (run_dir / "schema_report.json").write_text(json.dumps({"errors": 1 if failing else 0}))
    (tmp_path / "replay").mkdir(parents=True, exist_ok=True)
    (tmp_path / "replay" / "report.json").write_text(json.dumps({"run_a": "a", "run_b": "b", "fingerprint_equal": not failing}))
    return run_dir


def test_diagnose_success(tmp_path: Path, capsys):
    run_id = "r1"
    run_dir = _write_run(tmp_path, run_id, failing=False)
    output, failures = diagnose.diagnose(run_id, run_dir, tmp_path)
    assert "Run: r1" in output
    assert "Gates:" in output
    assert failures == []


def test_diagnose_failure_exit(tmp_path: Path):
    run_id = "r2"
    run_dir = _write_run(tmp_path, run_id, failing=True)
    output, failures = diagnose.diagnose(run_id, run_dir, tmp_path)
    assert failures  # should be non-empty
    assert "failure_category" not in failures
