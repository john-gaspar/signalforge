import os
import subprocess
from pathlib import Path

import pytest

from sentinelqa.ci import check_baseline_changes


def _run(cmd, cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


def _init_repo(tmp_path: Path) -> Path:
    _run(["git", "init"], cwd=tmp_path)
    _run(["git", "config", "user.email", "ci@example.com"], cwd=tmp_path)
    _run(["git", "config", "user.name", "CI"], cwd=tmp_path)
    path = tmp_path / "sentinelqa" / "baselines"
    path.mkdir(parents=True, exist_ok=True)
    (path / "foo.json").write_text("{}\n")
    _run(["git", "add", "."], cwd=tmp_path)
    _run(["git", "commit", "-m", "init"], cwd=tmp_path)
    return tmp_path


def test_baseline_guard_allows_no_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = _init_repo(tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    with pytest.raises(SystemExit) as exc:
        check_baseline_changes.main()
    assert exc.value.code == 0


def test_baseline_guard_blocks_baseline_change(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = _init_repo(tmp_path)
    # second commit with baseline change
    (repo / "sentinelqa" / "baselines" / "foo.json").write_text('{"changed": true}\n')
    _run(["git", "add", "."], cwd=repo)
    _run(["git", "commit", "-m", "update baseline"], cwd=repo)

    monkeypatch.chdir(repo)
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")

    with pytest.raises(SystemExit) as exc:
        check_baseline_changes.main()
    assert exc.value.code == 1


def test_baseline_guard_allows_with_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = _init_repo(tmp_path)
    (repo / "sentinelqa" / "baselines" / "foo.json").write_text('{"changed": true}\n')
    _run(["git", "add", "."], cwd=repo)
    _run(["git", "commit", "-m", "update baseline"], cwd=repo)

    monkeypatch.chdir(repo)
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("BASELINE_UPDATE", "1")

    with pytest.raises(SystemExit) as exc:
        check_baseline_changes.main()
    assert exc.value.code == 0
