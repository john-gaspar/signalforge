import json
from pathlib import Path

import pytest

from sentinelqa.gates import runner


def _cmd(exit_code: int) -> list[str]:
    return [runner.sys.executable, "-c", f"import sys; sys.exit({exit_code})"]


def test_gate_runner_writes_ordered_ledger(tmp_path: Path):
    run_id = "r-ledger"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    gate_cmds = {"g1": _cmd(0), "g2": _cmd(0)}
    order = ["g1", "g2"]
    ledger, failed = runner.run_gate_sequence(run_id, run_dir, required=order, gate_order=order, gate_commands=gate_cmds)

    assert failed is None
    ledger_path = run_dir / "gates.json"
    data = json.loads(ledger_path.read_text())
    assert [g["name"] for g in data["gates"]] == order
    assert all(g["status"] == "pass" for g in data["gates"])


def test_gate_runner_fails_on_required_gate(tmp_path: Path):
    run_id = "r-fail"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    gate_cmds = {"g1": _cmd(0), "g2": _cmd(1)}
    order = ["g1", "g2"]
    ledger, failed = runner.run_gate_sequence(run_id, run_dir, required=order, gate_order=order, gate_commands=gate_cmds)

    assert failed == "g2"
    data = json.loads((run_dir / "gates.json").read_text())
    assert data["gates"][1]["status"] == "fail"


def test_gate_runner_unknown_gate_errors(tmp_path: Path):
    run_id = "r-unknown"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    with pytest.raises(ValueError):
        runner.run_gate_sequence(run_id, run_dir, required=["missing"], gate_order=["missing"], gate_commands={"g1": _cmd(0)})
