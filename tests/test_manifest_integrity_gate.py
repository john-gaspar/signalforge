import json
from pathlib import Path

import pytest

from sentinelqa.artifacts.manifest import write_manifest, validate_manifest


REQUIRED = ["events.json", "clusters.json", "summary.json", "alert.json", "metrics.json"]


def _write_artifacts(run_dir: Path, run_id: str):
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "events.json").write_text(json.dumps([{"event_id": "e1"}]))
    (run_dir / "clusters.json").write_text(json.dumps([{"cluster_id": "c1"}]))
    (run_dir / "summary.json").write_text(json.dumps({"summary": "ok"}))
    (run_dir / "alert.json").write_text(json.dumps({"decision": "sent"}))
    (run_dir / "metrics.json").write_text(json.dumps({"run_id": run_id, "events": 1}))


def test_manifest_integrity_happy_path(tmp_path: Path):
    run_id = "r1"
    run_dir = tmp_path / "runs" / run_id
    _write_artifacts(run_dir, run_id)
    manifest_path = write_manifest(run_dir, run_id, REQUIRED)
    errors = validate_manifest(manifest_path)
    assert errors == []


def test_manifest_detects_tamper(tmp_path: Path):
    run_id = "r2"
    run_dir = tmp_path / "runs" / run_id
    _write_artifacts(run_dir, run_id)
    manifest_path = write_manifest(run_dir, run_id, REQUIRED)

    # tamper
    (run_dir / "events.json").write_text(json.dumps([{"event_id": "e1"}, {"event_id": "e2"}]))

    errors = validate_manifest(manifest_path)
    assert any("sha mismatch" in e for e in errors)


def test_manifest_detects_missing_file(tmp_path: Path):
    run_id = "r3"
    run_dir = tmp_path / "runs" / run_id
    _write_artifacts(run_dir, run_id)
    manifest_path = write_manifest(run_dir, run_id, REQUIRED)

    (run_dir / "alert.json").unlink()

    errors = validate_manifest(manifest_path)
    assert any("missing" in e for e in errors)
