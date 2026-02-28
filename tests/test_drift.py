from sentinelqa.dq import drift


def test_compare_pass_with_matching_values():
    baseline = {
        "policy": {"default_numeric_tolerance": {"type": "absolute", "value": 0}},
        "checks": {
            "events.total": {"mode": "numeric", "baseline": 1},
            "events.by_type": {
                "mode": "distribution",
                "baseline": {"a": 1},
                "tolerance": {"type": "percent_points", "value": 5.0},
            },
        },
    }
    current = {
        "events": {"total": 1, "by_type": {"a": 1}},
    }

    diffs = drift.compare(baseline, current)
    assert diffs == []


def test_compare_fails_on_distribution_drift():
    baseline = {
        "policy": {"default_dist_tolerance": {"type": "percent_points", "value": 0.0}},
        "checks": {
            "events.by_type": {
                "mode": "distribution",
                "baseline": {"a": 2},
            },
        },
    }
    current = {
        "events": {"by_type": {"a": 1, "b": 1}},
    }

    diffs = drift.compare(baseline, current)
    assert diffs, "expected a drift diff"
    assert "events.by_type" in diffs[0]


def test_optional_check_is_skipped_when_missing():
    baseline = {
        "checks": {
            "events.by_severity": {
                "mode": "distribution",
                "baseline": {"high": 1},
                "optional": True,
            },
        },
    }
    current = {
        "events": {"by_type": {"a": 1}},
    }

    diffs = drift.compare(baseline, current)
    assert diffs == []
