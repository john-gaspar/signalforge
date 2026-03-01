from sentinelqa.gates.gate_contract_index import validate_contract_index, INDEX_PATH
from sentinelqa.gates import runner
import json
from pathlib import Path


def test_contract_index_matches_defaults(tmp_path: Path, monkeypatch):
    # copy real index into temp to avoid mutating repo file
    idx_copy = tmp_path / "contracts_index.json"
    idx_copy.write_text(INDEX_PATH.read_text())
    monkeypatch.setattr("sentinelqa.gates.gate_contract_index.INDEX_PATH", idx_copy)

    issues = validate_contract_index()
    assert issues == []


def test_contract_index_detects_gate_order_change(tmp_path: Path, monkeypatch):
    idx_copy = tmp_path / "contracts_index.json"
    data = json.loads(INDEX_PATH.read_text())
    data["gates_order"] = data["gates_order"][1:]  # drop first
    idx_copy.write_text(json.dumps(data))
    monkeypatch.setattr("sentinelqa.gates.gate_contract_index.INDEX_PATH", idx_copy)

    issues = validate_contract_index()
    assert any("runner_gate_order" in i for i in issues)
