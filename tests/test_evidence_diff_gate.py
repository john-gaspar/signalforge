import json
import sys
from pathlib import Path

import pytest

from sentinelqa.gates import gate_evidence_diff


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def test_evidence_diff_reports_changes(tmp_path: Path):
    # baseline bundle
    baseline_dir = tmp_path / "baseline"
    _write_json(
        baseline_dir / "manifest.json",
        {
            "files": [
                {"path": "alert.json", "sha256": "base-alert"},
                {"path": "clusters.json", "sha256": "base-clusters"},
                {"path": "summary.json", "sha256": "base-summary"},
            ],
            "fingerprint_sha256": "fp-base",
        },
    )
    _write_json(baseline_dir / "schema_report.json", {"errors": [], "schema_version": "v1"})
    _write_json(
        baseline_dir / "bench_expected.json",
        {"cases_succeeded": 10, "cases_total": 10, "p95_latency_ms": 100, "accuracy": {"f1": 0.9}},
    )

    # current artifacts
    artifacts_root = tmp_path / "artifacts"
    run_id = "r1"
    run_dir = artifacts_root / "runs" / run_id
    _write_json(
        run_dir / "manifest.json",
        {
            "files": [
                {"path": "alert.json", "sha256": "current-alert"},  # changed
                {"path": "clusters.json", "sha256": "base-clusters"},  # unchanged
                {"path": "extra.json", "sha256": "new"},  # added
            ],
            "fingerprint_sha256": "fp-current",
        },
    )
    _write_json(run_dir / "schema_report.json", {"errors": [1, 2], "schema_version": "v2"})
    _write_json(
        artifacts_root / "bench" / "latest.json",
        {"cases_succeeded": 8, "cases_total": 10, "p95_latency_ms": 150, "accuracy": {"f1": 0.7}},
    )

    diff = gate_evidence_diff.compute_diff(run_id, run_dir, artifacts_root, baseline_dir)

    assert diff["manifest"]["changed"] == ["alert.json"]
    assert diff["manifest"]["added"] == ["extra.json"]
    assert diff["manifest"]["removed"] == ["summary.json"]
    assert diff["schema"]["delta_errors"] == 2
    assert diff["bench"]["delta"]["pass_rate"] == pytest.approx(-0.2)
    assert diff["bench"]["delta"]["f1"] == pytest.approx(-0.2)
    assert diff["bench"]["delta"]["p95_latency_ms"] == 50
    assert (run_dir / "evidence_diff.json").exists()


def _prepare_baseline_and_run(tmp_path: Path, current_schema_errors: int, missing_manifest_paths: list[str]) -> tuple[Path, Path, str]:
    baseline_dir = tmp_path / "baseline"
    run_id = "r-break"
    artifacts_root = tmp_path / "artifacts"
    run_dir = artifacts_root / "runs" / run_id

    _write_json(
        baseline_dir / "manifest.json",
        {"files": [{"path": p, "sha256": "base"} for p in ["events.json", "extra.json"]], "fingerprint_sha256": "fp-base"},
    )
    _write_json(baseline_dir / "schema_report.json", {"errors": 0})
    _write_json(baseline_dir / "bench_expected.json", {"cases_succeeded": 10, "cases_total": 10, "p95_latency_ms": 100, "accuracy": {"f1": 0.9}})

    # Current manifest missing some paths
    current_files = [{"path": p, "sha256": "cur"} for p in ["events.json"] if p not in missing_manifest_paths]
    _write_json(run_dir / "manifest.json", {"files": current_files, "fingerprint_sha256": "fp-cur"})
    _write_json(run_dir / "schema_report.json", {"errors": current_schema_errors})
    _write_json(artifacts_root / "bench" / "latest.json", {"cases_succeeded": 10, "cases_total": 10, "p95_latency_ms": 90, "accuracy": {"f1": 0.95}})
    (artifacts_root / "latest_seed_run_id").write_text(run_id)
    return baseline_dir, artifacts_root, run_id


def _run_gate(monkeypatch: pytest.MonkeyPatch, baseline_dir: Path, artifacts_root: Path, mode: str, baseline_update: str | None = None) -> int:
    argv = [
        "prog",
        "--artifacts-dir",
        str(artifacts_root),
        "--baseline-dir",
        str(baseline_dir),
        "--mode",
        mode,
    ]
    monkeypatch.delenv("EVIDENCE_DIFF_MODE", raising=False)
    if baseline_update is not None:
        monkeypatch.setenv("BASELINE_UPDATE", baseline_update)
    else:
        monkeypatch.delenv("BASELINE_UPDATE", raising=False)
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc:
        gate_evidence_diff.main()
    return exc.value.code


def test_evidence_diff_schema_regression_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    baseline_dir, artifacts_root, _ = _prepare_baseline_and_run(tmp_path, current_schema_errors=2, missing_manifest_paths=[])
    code = _run_gate(monkeypatch, baseline_dir, artifacts_root, mode="fail")
    assert code == 1


def test_evidence_diff_manifest_removal_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    baseline_dir, artifacts_root, _ = _prepare_baseline_and_run(tmp_path, current_schema_errors=0, missing_manifest_paths=["extra.json"])
    code = _run_gate(monkeypatch, baseline_dir, artifacts_root, mode="fail")
    assert code == 1


def test_evidence_diff_baseline_update_bypasses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    baseline_dir, artifacts_root, _ = _prepare_baseline_and_run(tmp_path, current_schema_errors=2, missing_manifest_paths=["extra.json"])
    code = _run_gate(monkeypatch, baseline_dir, artifacts_root, mode="fail", baseline_update="1")
    assert code == 0
