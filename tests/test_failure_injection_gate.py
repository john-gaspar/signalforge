import json
from pathlib import Path

from sentinelqa.gates.gate_failure_injection import (
    _scenario_socket_unavailable,
    _scenario_artifact_tamper,
    run_failure_injection,
)
from sentinelqa.artifacts.manifest import write_manifest


def test_socket_unavailable_passes():
    res = _scenario_socket_unavailable("redis_unavailable", "redis.invalid", 6379, "infra.redis")
    assert res["status"] == "pass"
    assert res["category"] == "infra.redis"


def test_artifact_tamper_detects_integrity(tmp_path: Path):
    run_id = "r1"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    # minimal artifacts + manifest
    (run_dir / "events.json").write_text(json.dumps([{"event_id": "e1", "source": "s", "normalized": {"subject": "", "body": ""}, "raw_file": "f"}]))
    (run_dir / "clusters.json").write_text(json.dumps([{"cluster_id": "c1", "members": ["e1"]}]))
    (run_dir / "summary.json").write_text(json.dumps({"issue": "x", "cluster_count": 1, "evidence": []}))
    (run_dir / "alert.json").write_text(json.dumps({"decision": "sent", "channel": "c", "text": "t"}))
    (run_dir / "metrics.json").write_text(json.dumps({"run_id": run_id, "events": 1, "clusters": 1, "alerts_sent": 1, "latency_ms": 1}))
    write_manifest(run_dir, run_id, ["events.json", "clusters.json", "summary.json", "alert.json", "metrics.json"])

    res = _scenario_artifact_tamper(run_id, run_dir)
    assert res["status"] == "pass"
    assert res["category"] == "artifact.integrity"


def test_run_failure_injection_shapes(tmp_path: Path):
    run_id = "r2"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "events.json").write_text(json.dumps([{"event_id": "e1", "source": "s", "normalized": {"subject": "", "body": ""}, "raw_file": "f"}]))
    (run_dir / "clusters.json").write_text(json.dumps([{"cluster_id": "c1", "members": ["e1"]}]))
    (run_dir / "summary.json").write_text(json.dumps({"issue": "x", "cluster_count": 1, "evidence": []}))
    (run_dir / "alert.json").write_text(json.dumps({"decision": "sent", "channel": "c", "text": "t"}))
    (run_dir / "metrics.json").write_text(json.dumps({"run_id": run_id, "events": 1, "clusters": 1, "alerts_sent": 1, "latency_ms": 1}))
    write_manifest(run_dir, run_id, ["events.json", "clusters.json", "summary.json", "alert.json", "metrics.json"])

    results = run_failure_injection(run_id, run_dir)
    names = {r["name"] for r in results}
    assert {"redis_unavailable", "neo4j_unavailable", "artifact_tamper"} <= names
