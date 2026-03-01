from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

from sentinelqa.gates import runner
from sentinelqa.gates.gate_run_contract import REQUIRED_FILES as RUN_CONTRACT_REQUIRED
from sentinelqa.gates.gate_artifact_schema import REQUIRED_FILES as SCHEMA_REQUIRED

INDEX_PATH = Path(__file__).resolve().parents[1] / "contracts" / "contracts_index.json"


def _load_index() -> Dict[str, Any]:
    return json.loads(INDEX_PATH.read_text())


def _diff_lists(name: str, actual: List[str], expected: List[str], order_matters: bool = True) -> List[str]:
    if order_matters:
        if actual != expected:
            return [f"{name} mismatch: expected {expected}, got {actual}"]
        return []
    if set(actual) != set(expected):
        return [f"{name} set mismatch: expected {set(expected)}, got {set(actual)}"]
    return []


def validate_contract_index() -> List[str]:
    idx = _load_index()
    issues: List[str] = []

    issues += _diff_lists("required_artifacts", RUN_CONTRACT_REQUIRED, idx["required_artifacts"], order_matters=False)
    issues += _diff_lists("schema_required_artifacts", SCHEMA_REQUIRED, list(idx["schemas_v1"].keys()), order_matters=False)
    issues += _diff_lists("runner_gate_order", runner.DEFAULT_ORDER, idx["gates_order"], order_matters=True)

    if idx.get("bench_baseline_path") != "sentinelqa/baselines/bench_baseline.json":
        issues.append("bench_baseline_path mismatch")

    return issues


def main() -> None:
    if not INDEX_PATH.exists():
        print(f"[FAIL] contracts index missing at {INDEX_PATH}")
        sys.exit(1)

    issues = validate_contract_index()
    if issues:
        print("[FAIL] contract index gate")
        for issue in issues:
            print(f" - {issue}")
        sys.exit(1)

    print("[PASS] contract index gate")
    sys.exit(0)


if __name__ == "__main__":
    main()
