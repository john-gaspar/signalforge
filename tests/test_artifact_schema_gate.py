import json
from pathlib import Path

import pytest

from sentinelqa.gates.gate_artifact_schema import validate_artifacts
from sentinelqa.gates.gate_artifact_schema import REQUIRED_FILES
from sentinelqa.gates.gate_artifact_schema import _discover_run


def _write_valid_artifacts(run_dir: Path, run_id: str):
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "tickets.json").write_text(
        json.dumps(
            {
                "version": 1,
                "tickets": [
                    {
                        "id": "t1",
                        "subject": "s",
                        "description": "d",
                        "created_at": "now",
                        "updated_at": "now",
                        "tags": [],
                        "status": "open",
                    }
                ],
            }
        )
    )
    (run_dir / "events.json").write_text(json.dumps([{"event_id": "e1", "source": "fixture", "normalized": {"subject": "", "body": ""}, "raw_file": "f"}]))
    (run_dir / "clusters.json").write_text(json.dumps([{"cluster_id": "c1", "members": ["e1"]}]))
    (run_dir / "summary.json").write_text(json.dumps({"issue": "x", "cluster_count": 1, "evidence": [{"cluster_id": "c1", "members": ["e1"]}]}))
    (run_dir / "alert.json").write_text(json.dumps({"decision": "sent", "channel": "#alerts", "text": "t"}))
    (run_dir / "metrics.json").write_text(json.dumps({"run_id": run_id, "events": 1, "clusters": 1, "alerts_sent": 1, "latency_ms": 1}))


def test_artifact_schema_pass(tmp_path: Path):
    run_id = "r1"
    artifacts_root = tmp_path / "artifacts"
    run_dir = artifacts_root / "runs" / run_id
    _write_valid_artifacts(run_dir, run_id)
    (artifacts_root / "latest_seed_run_id").write_text(run_id)

    errors = validate_artifacts(run_dir)
    assert errors == []


def test_artifact_schema_detects_invalid(tmp_path: Path):
    run_id = "r2"
    artifacts_root = tmp_path / "artifacts"
    run_dir = artifacts_root / "runs" / run_id
    _write_valid_artifacts(run_dir, run_id)
    # break metrics
    (run_dir / "metrics.json").write_text(json.dumps({"run_id": run_id}))

    errors = validate_artifacts(run_dir)
    assert any("metrics.json" in e for e in errors)


def test_discover_run_missing(tmp_path: Path):
    artifacts_root = tmp_path / "artifacts"
    with pytest.raises(SystemExit):
        _discover_run(artifacts_root, None)
