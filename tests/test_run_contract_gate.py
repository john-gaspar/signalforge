import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from sentinelqa.gates.gate_run_contract import validate_run_contract


def _timestamps():
    now = datetime.now(timezone.utc)
    return {
        "created_at": now.isoformat(),
        "started_at": (now + timedelta(seconds=1)).isoformat(),
        "ended_at": (now + timedelta(seconds=2)).isoformat(),
    }


def _write_artifacts(run_dir: Path, run_id: str) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "events.json").write_text(json.dumps([{"event_id": "e1"}]))
    (run_dir / "clusters.json").write_text(json.dumps([{"cluster_id": "c1"}]))
    (run_dir / "summary.json").write_text(json.dumps({"summary": "ok"}))
    (run_dir / "alert.json").write_text(json.dumps({"decision": "sent"}))
    metrics = {
        "run_id": run_id,
        "events": 1,
        "clusters": 1,
        "alerts_sent": 1,
        "latency_ms": 10,
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics))


def test_run_contract_valid(tmp_path: Path):
    run_id = "r1"
    run_dir = tmp_path / "runs" / run_id
    _write_artifacts(run_dir, run_id)
    bench = tmp_path / "bench" / "latest.json"
    bench.parent.mkdir(parents=True, exist_ok=True)
    bench.write_text(json.dumps({"run_id": run_id}))

    ts = _timestamps()
    record = {
        "run_id": run_id,
        "status": "succeeded",
        "created_at": ts["created_at"],
        "started_at": ts["started_at"],
        "ended_at": ts["ended_at"],
        "metrics": {"events": 1},
        "error": None,
    }

    errors = validate_run_contract(run_dir, record, bench, require_bench=True)
    assert errors == []


def test_run_contract_missing_bench_fails(tmp_path: Path):
    run_id = "r2"
    run_dir = tmp_path / "runs" / run_id
    _write_artifacts(run_dir, run_id)
    bench = tmp_path / "bench" / "latest.json"  # not created
    ts = _timestamps()
    record = {
        "run_id": run_id,
        "status": "succeeded",
        "created_at": ts["created_at"],
        "started_at": ts["started_at"],
        "ended_at": ts["ended_at"],
        "metrics": {"events": 1},
        "error": None,
    }

    errors = validate_run_contract(run_dir, record, bench, require_bench=True)
    assert any("bench report missing" in e for e in errors)


def test_run_contract_illegal_transition(tmp_path: Path):
    run_id = "r3"
    run_dir = tmp_path / "runs" / run_id
    _write_artifacts(run_dir, run_id)
    bench = tmp_path / "bench" / "latest.json"
    bench.parent.mkdir(parents=True, exist_ok=True)
    bench.write_text(json.dumps({"run_id": run_id}))

    ts = _timestamps()
    record = {
        "run_id": run_id,
        "status": "succeeded",
        "created_at": ts["created_at"],
        "started_at": ts["started_at"],
        "ended_at": None,  # illegal for succeeded
        "metrics": {"events": 1},
        "error": None,
    }

    errors = validate_run_contract(run_dir, record, bench, require_bench=True)
    assert any("ended_at missing" in e for e in errors)


def test_run_contract_allows_small_clock_skew(tmp_path: Path):
    run_id = "r4"
    run_dir = tmp_path / "runs" / run_id
    _write_artifacts(run_dir, run_id)
    bench = tmp_path / "bench" / "latest.json"
    bench.parent.mkdir(parents=True, exist_ok=True)
    bench.write_text(json.dumps({"run_id": run_id}))

    now = datetime.now(timezone.utc)
    record = {
        "run_id": run_id,
        "status": "succeeded",
        "created_at": now.isoformat(),
        "started_at": (now - timedelta(seconds=10)).isoformat(),  # 10s skew
        "ended_at": (now + timedelta(seconds=2)).isoformat(),
        "metrics": {"events": 1},
        "error": None,
    }

    errors = validate_run_contract(run_dir, record, bench, require_bench=True, max_clock_skew_s=300)
    assert errors == []


def test_run_contract_fails_on_large_clock_skew(tmp_path: Path):
    run_id = "r5"
    run_dir = tmp_path / "runs" / run_id
    _write_artifacts(run_dir, run_id)
    bench = tmp_path / "bench" / "latest.json"
    bench.parent.mkdir(parents=True, exist_ok=True)
    bench.write_text(json.dumps({"run_id": run_id}))

    now = datetime.now(timezone.utc)
    record = {
        "run_id": run_id,
        "status": "succeeded",
        "created_at": now.isoformat(),
        "started_at": (now - timedelta(minutes=10)).isoformat(),  # 10 minutes early
        "ended_at": (now + timedelta(seconds=2)).isoformat(),
        "metrics": {"events": 1},
        "error": None,
    }

    errors = validate_run_contract(run_dir, record, bench, require_bench=True, max_clock_skew_s=300)
    assert any("started_at earlier than created_at" in e for e in errors)
