import json
from pathlib import Path

import pytest

from sentinelqa.gates import load_gate
from sentinelqa.load import report as load_report


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def test_load_gate_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    report = {
        "success_rate": 0.995,
        "enqueue_latency_ms_p95": 200,
        "completion_time_s_p95": 10,
        "throughput_rpm": 20,
    }
    baseline = {
        "min_success_rate": 0.99,
        "max_enqueue_latency_ms_p95": 500,
        "max_completion_time_s_p95": 30,
        "min_throughput_rpm": 10,
    }
    report_path = tmp_path / "latest.json"
    baseline_path = tmp_path / "baseline.json"
    write_json(report_path, report)
    write_json(baseline_path, baseline)
    monkeypatch.setenv("LOAD_REPORT_PATH", str(report_path))
    monkeypatch.setenv("LOAD_BASELINE_PATH", str(baseline_path))

    with pytest.raises(SystemExit) as exc:
        load_gate.main()
    assert exc.value.code == 0


def test_load_gate_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    report = {
        "success_rate": 0.9,
        "enqueue_latency_ms_p95": 600,
        "completion_time_s_p95": 40,
        "throughput_rpm": 5,
    }
    baseline = {
        "min_success_rate": 0.99,
        "max_enqueue_latency_ms_p95": 500,
        "max_completion_time_s_p95": 30,
        "min_throughput_rpm": 10,
    }
    report_path = tmp_path / "latest.json"
    baseline_path = tmp_path / "baseline.json"
    write_json(report_path, report)
    write_json(baseline_path, baseline)
    monkeypatch.setenv("LOAD_REPORT_PATH", str(report_path))
    monkeypatch.setenv("LOAD_BASELINE_PATH", str(baseline_path))

    with pytest.raises(SystemExit) as exc:
        load_gate.main()
    assert exc.value.code == 1


def test_load_gate_completion_tolerance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    report = {
        "success_rate": 1.0,
        "enqueue_latency_ms_p95": 100,
        "completion_time_s_p95": 50,  # slower than baseline but within tol
        "throughput_rpm": 12,
    }
    baseline = {
        "min_success_rate": 0.99,
        "max_enqueue_latency_ms_p95": 500,
        "max_completion_time_s_p95": 40,
        "min_throughput_rpm": 10,
    }
    report_path = tmp_path / "latest.json"
    baseline_path = tmp_path / "baseline.json"
    write_json(report_path, report)
    write_json(baseline_path, baseline)
    monkeypatch.setenv("LOAD_REPORT_PATH", str(report_path))
    monkeypatch.setenv("LOAD_BASELINE_PATH", str(baseline_path))
    monkeypatch.setenv("LOAD_COMPLETION_TOL_PCT", "0.5")  # allow 50% slower

    with pytest.raises(SystemExit) as exc:
        load_gate.main()
    assert exc.value.code == 0


def test_report_handles_no_samples(tmp_path: Path):
    raw = {
        "requests_total": 10,
        "requests_failed": 0,
        "success_rate": 1.0,
        "enqueue_latency_ms_p50": 3,
        "enqueue_latency_ms_p95": 7,
        "completion_time_s_p50": 0.01,
        "completion_time_s_p95": 0.02,
        "runs_succeeded": 10,
        "runs_failed": 0,
        "duration_s": 30,
        "users": 2,
        "spawn_rate": 1,
    }
    raw_path = tmp_path / "raw.json"
    out_path = tmp_path / "latest.json"
    write_json(raw_path, raw)

    result = load_report.generate_report(raw_path, out_path)

    assert "completion_time_s_p95" in result
    assert result["completion_time_s_p95"] == 0.02
    assert out_path.exists()
