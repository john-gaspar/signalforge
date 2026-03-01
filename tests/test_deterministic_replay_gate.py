import json
from pathlib import Path

from sentinelqa.gates.gate_deterministic_replay import _compare_runs


def test_compare_runs_fails_on_fingerprint_mismatch(tmp_path: Path):
    run_a = tmp_path / "runs" / "a"
    run_b = tmp_path / "runs" / "b"
    run_a.mkdir(parents=True)
    run_b.mkdir(parents=True)
    (run_a / "manifest.json").write_text(json.dumps({"fingerprint_sha256": "aaa"}))
    (run_b / "manifest.json").write_text(json.dumps({"fingerprint_sha256": "bbb"}))
    (run_a / "metrics.json").write_text(json.dumps({"x": 1}))
    (run_b / "metrics.json").write_text(json.dumps({"x": 1}))

    report = _compare_runs(("a", run_a), ("b", run_b))
    assert report["fingerprint_equal"] is False
