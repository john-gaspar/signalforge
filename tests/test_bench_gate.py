from __future__ import annotations

import json
from pathlib import Path

from sentinelqa.gates import bench_gate
from sentinelqa.bench import run as bench_run


def write(path: Path, obj: dict):
    path.write_text(json.dumps(obj))


def test_bench_gate_pass(tmp_path: Path):
    baseline = {"min_pass_rate": 1.0, "max_p95_latency_ms": 2000}
    current = {"cases_total": 2, "cases_succeeded": 2, "p95_latency_ms": 1500}
    errors = bench_gate.compare(baseline, current)
    assert errors == []


def test_bench_gate_fail_latency(tmp_path: Path):
    baseline = {"min_pass_rate": 1.0, "max_p95_latency_ms": 100}
    current = {"cases_total": 2, "cases_succeeded": 2, "p95_latency_ms": 150}
    errors = bench_gate.compare(baseline, current)
    assert any("p95_latency_ms" in e for e in errors)


def test_bench_gate_fail_pass_rate(tmp_path: Path):
    baseline = {"min_pass_rate": 0.9, "max_p95_latency_ms": 1000}
    current = {"cases_total": 2, "cases_succeeded": 1, "p95_latency_ms": 500}
    errors = bench_gate.compare(baseline, current)
    assert any("pass_rate" in e for e in errors)


def test_missing_result_triggers_generation(monkeypatch, tmp_path: Path):
    baseline_path = tmp_path / "baseline.json"
    result_path = tmp_path / "artifacts/bench/latest.json"
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "expectations.json").write_text(json.dumps({"min_events": 0, "min_clusters": 0, "required_keys": []}))
    write(baseline_path, {"min_pass_rate": 0.0, "max_p95_latency_ms": 9999})

    def fake_run(base_url, fixtures_dir, out_path):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        write(out_path, {"cases_total": 1, "cases_succeeded": 1, "p95_latency_ms": 1})
        return json.loads(out_path.read_text())

    monkeypatch.setenv("BENCH_BASELINE_PATH", str(baseline_path))
    monkeypatch.setenv("BENCH_RESULT_PATH", str(result_path))
    monkeypatch.setenv("BENCH_FIXTURES", str(fixtures))
    monkeypatch.setenv("BENCH_BASE_URL", "http://api:8000")
    monkeypatch.setattr(bench_gate, "run_benchmark", fake_run)

    import pytest
    with pytest.raises(SystemExit) as exc:
        bench_gate.main()
    assert exc.value.code == 0
