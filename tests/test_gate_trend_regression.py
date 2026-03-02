import json
from pathlib import Path

import pytest

from sentinelqa.gates import gate_trend_regression as gate


def _write_thresholds(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "trend:",
                "  window: 10",
                "  min_history: 5",
                "  max_negative_f1_slope: -0.001",
                "  max_negative_pass_slope: -0.001",
                "  max_positive_latency_slope: 1.0",
                "",
            ]
        )
    )


def _write_history(tmp_path: Path, entries: list[dict]) -> Path:
    history_path = tmp_path / "bench" / "history.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    return history_path


def _entry(run_suffix: int, f1: float, pass_rate: float, latency: float) -> dict:
    return {
        "timestamp": f"2024-01-0{run_suffix}T00:00:00Z",
        "run_id": f"run{run_suffix}",
        "f1": f1,
        "pass_rate": pass_rate,
        "p95_latency_ms": latency,
    }


def test_trend_regression_pass(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    thresholds_path = tmp_path / "sentinelqa" / "gates" / "thresholds.yaml"
    _write_thresholds(thresholds_path)
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path))
    monkeypatch.setattr(gate, "THRESHOLDS_PATH", thresholds_path)

    entries = [
        _entry(i, 0.80 + i * 0.01, 0.90 + i * 0.002, 300 - i * 5) for i in range(1, 7)
    ]
    _write_history(tmp_path, entries)

    with pytest.raises(SystemExit) as excinfo:
        gate.main()
    assert excinfo.value.code == 0


def test_trend_regression_fail_on_f1(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    thresholds_path = tmp_path / "sentinelqa" / "gates" / "thresholds.yaml"
    _write_thresholds(thresholds_path)
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path))
    monkeypatch.setattr(gate, "THRESHOLDS_PATH", thresholds_path)

    entries = [
        _entry(i, 0.95 - i * 0.05, 0.95, 250) for i in range(1, 7)
    ]
    _write_history(tmp_path, entries)

    with pytest.raises(SystemExit) as excinfo:
        gate.main()
    assert excinfo.value.code == 1


def test_trend_regression_skips_when_insufficient_history(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    thresholds_path = tmp_path / "sentinelqa" / "gates" / "thresholds.yaml"
    _write_thresholds(thresholds_path)
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path))
    monkeypatch.setattr(gate, "THRESHOLDS_PATH", thresholds_path)

    entries = [_entry(i, 0.9, 0.95, 250) for i in range(1, 3)]
    _write_history(tmp_path, entries)

    with pytest.raises(SystemExit) as excinfo:
        gate.main()
    assert excinfo.value.code == 0
