import json
from pathlib import Path

import pytest

from sentinelqa.gates.gate_slo import validate_slo


def _write_metadata(tmp_path: Path, overrides=None):
    overrides = overrides or {}
    meta = {
        "run_id": "r1",
        "run_duration_ms": 1000,
        "final_status": "succeeded",
        "state_transition_path": ["queued", "running", "succeeded"],
        "gate_results": [{"name": "metrics_gate", "status": "pass"}],
        "failure_category": "none",
    }
    meta.update(overrides)
    run_dir = tmp_path / "runs" / meta["run_id"]
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_metadata.json").write_text(json.dumps(meta))
    return meta, run_dir


def test_slo_gate_pass(tmp_path: Path):
    meta, _ = _write_metadata(tmp_path)
    errors = validate_slo(meta, max_ms=2000)
    assert errors == []


def test_slo_gate_duration_fail(tmp_path: Path):
    meta, _ = _write_metadata(tmp_path, {"run_duration_ms": 5000})
    errors = validate_slo(meta, max_ms=1000)
    assert any("run_duration_ms" in e for e in errors)


def test_slo_gate_failure_category_required_on_failed(tmp_path: Path):
    meta, _ = _write_metadata(tmp_path, {"final_status": "failed"})
    errors = validate_slo(meta, max_ms=2000)
    assert any("failure_category" in e for e in errors)


def test_slo_gate_disallows_invalid_category(tmp_path: Path):
    meta, _ = _write_metadata(tmp_path, {"failure_category": "weird"})
    errors = validate_slo(meta, max_ms=2000)
    assert any("not allowed" in e for e in errors)
