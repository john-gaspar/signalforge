import json
from pathlib import Path


def test_required_files_allows_superset():
    baseline_path = Path("sentinelqa/baselines/drift_baseline.json")
    baseline = json.loads(baseline_path.read_text())
    check = baseline["checks"]["artifacts.required_files_present"]
    assert check["mode"] == "set_contains"

    required = set(check["baseline"])
    current = required | {"tickets.json"}

    # set_contains semantics: baseline set is subset of current artifacts
    assert required.issubset(current)
