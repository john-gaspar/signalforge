from pathlib import Path

from sentinelqa.ci.diagnose_ci import diagnose


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_diagnose_outputs_summary(tmp_path: Path, capsys):
    artifacts = tmp_path / "artifacts"
    run_id = "run123"
    _write(artifacts / "latest_seed_run_id", run_id)
    run_dir = artifacts / "runs" / run_id
    _write(
        run_dir / "gates.json",
        '{"gates":[{"name":"graph","status":"pass"},{"name":"bench","status":"fail","error":"bench regression"}]}',
    )
    _write(run_dir / "run_metadata.json", '{"failure_category":"data_quality","run_duration_ms":1200}')
    _write(run_dir / "manifest.json", '{"fingerprint_sha256":"fp-abc"}')
    _write(run_dir / "schema_report.json", '{"errors":[1,2]}')
    _write(artifacts / "bench" / "latest.json", '{"cases_succeeded":8,"cases_total":10,"p95_latency_ms":150,"accuracy":{"f1":0.7}}')
    _write(run_dir / "evidence_diff.json", '{"manifest":{"changed":["alert.json"],"added":[],"removed":["metrics.json"]}}')

    lines = diagnose(str(artifacts))
    out = "\n".join(lines)

    assert "run run123" in out
    assert "first_fail=bench" in out
    assert "bench pass_rate=0.8" in out
    assert "schema_errors=2" in out
    assert "evidence_diff changed_files=2" in out
