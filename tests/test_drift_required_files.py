import json
from pathlib import Path

from sentinelqa.dq import drift


def _baseline():
    baseline_path = Path("sentinelqa/baselines/drift_baseline.json")
    return json.loads(baseline_path.read_text())


def test_required_files_allows_superset():
    baseline = _baseline()
    current = {
        "artifacts": {
            "required_files_present": baseline["checks"]["artifacts.required_files_present"]["baseline"]
            + ["tickets.json"]
        },
        "events": {
            "total": 1,
            "by_type": {},
            "by_severity": {},
        },
        "clusters": {"count": 1, "size_buckets": {"1": 1}},
        "metrics": {
            "required_keys_present": ["events", "clusters", "alerts_sent", "latency_ms"],
            "events": 1,
            "clusters": 1,
            "alerts_sent": 1,
            "stable_flags": {},
        },
    }
    diffs = drift.compare(baseline, current)
    assert diffs == []


def test_required_files_missing_core_fails():
    baseline = _baseline()
    current = {
        "artifacts": {
            "required_files_present": [
                "alert.json",
                "clusters.json",
                # missing metrics.json
                "events.json",
                "summary.json",
            ]
        }
    }
    diffs = drift.compare(baseline, current)
    assert any("metrics.json" in d for d in diffs)


def test_required_files_extras_allowed_even_if_exact_mode():
    baseline = _baseline()
    # force mode to exact to verify compare special-cases artifacts set to contains
    baseline["checks"]["artifacts.required_files_present"]["mode"] = "set_exact"
    current = {
        "artifacts": {
            "required_files_present": baseline["checks"]["artifacts.required_files_present"]["baseline"]
            + ["tickets.json"]
        },
        "events": {"total": 1, "by_type": {}, "by_severity": {}},
        "clusters": {"count": 1, "size_buckets": {"1": 1}},
        "metrics": {
            "required_keys_present": ["events", "clusters", "alerts_sent", "latency_ms"],
            "events": 1,
            "clusters": 1,
            "alerts_sent": 1,
            "stable_flags": {},
        },
    }
    diffs = drift.compare(baseline, current)
    assert diffs == []
