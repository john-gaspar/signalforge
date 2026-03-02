import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from sentinelqa.cli import run_capsule


def _setup_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "sentinelqa" / "gates").mkdir(parents=True)
    (repo / "sentinelqa" / "contracts").mkdir(parents=True)
    (repo / "sentinelqa" / "gates" / "thresholds.yaml").write_text("min_success_rate: 0.9\n")
    (repo / "sentinelqa" / "contracts" / "contracts_index.json").write_text("{}\n")

    artifacts = repo / "artifacts"
    run_id = "run123"
    run_dir = artifacts / "runs" / run_id
    run_dir.mkdir(parents=True)
    (artifacts / "latest_seed_run_id").write_text(run_id)
    (run_dir / "manifest.json").write_text("{}")
    (run_dir / "schema_report.json").write_text("{}")
    (run_dir / "gates.json").write_text("{}")
    return repo, run_dir


def test_pack_creates_capsule(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo, run_dir = _setup_repo(tmp_path)
    monkeypatch.setattr(run_capsule, "REPO_ROOT", repo)
    artifacts_root = repo / "artifacts"

    capsule_path = run_capsule.pack_capsule(None, artifacts_root)
    assert capsule_path.exists()

    with zipfile.ZipFile(capsule_path) as zf:
        names = zf.namelist()
    assert f"artifacts/runs/{run_dir.name}/manifest.json" in names
    assert "sentinelqa/gates/thresholds.yaml" in names
    assert "sentinelqa/contracts/contracts_index.json" in names


def test_replay_invokes_gates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo, _ = _setup_repo(tmp_path)
    monkeypatch.setattr(run_capsule, "REPO_ROOT", repo)
    artifacts_root = repo / "artifacts"
    capsule_path = run_capsule.pack_capsule(None, artifacts_root)

    calls = []

    def fake_run(cmd, cwd, capture_output, text):
        calls.append(SimpleNamespace(cmd=cmd, cwd=cwd))
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(run_capsule.subprocess, "run", fake_run)

    ok = run_capsule.replay_capsule(capsule_path)
    assert ok
    assert len(calls) == 3
    assert any("gate_manifest_integrity" in " ".join(c.cmd) for c in calls)
    assert all(c.cwd == repo for c in calls)
