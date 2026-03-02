from sentinelqa.ci.check_baseline_changes import evaluate_changed_paths


def test_no_changes_ok():
    ok, lines = evaluate_changed_paths([], allow=False)
    assert ok
    assert "[OK]" in lines[0]
    assert "no protected" in lines[0]


def test_protected_change_without_marker_fails():
    changed = [("M", "sentinelqa/schemas/events_v1.json")]
    ok, lines = evaluate_changed_paths(changed, allow=False)
    assert not ok
    assert "protected changes require intent marker" in lines[0]
    assert "events_v1.json" in "\n".join(lines)


def test_protected_change_with_marker_passes():
    changed = [("M", "sentinelqa/contracts/contracts_index.json"), ("A", ".baseline_update_intent")]
    ok, lines = evaluate_changed_paths(changed, allow=False)
    assert ok
    assert ".baseline_update_intent" in "\n".join(lines)


def test_new_schema_without_marker_fails():
    changed = [("A", "sentinelqa/schemas/new_schema.json")]
    ok, lines = evaluate_changed_paths(changed, allow=False)
    assert not ok
    assert "new_schema.json" in "\n".join(lines)


def test_allows_with_env_override():
    changed = [("M", "sentinelqa/baselines/foo.json")]
    ok, lines = evaluate_changed_paths(changed, allow=True)
    assert ok
    assert "BASELINE_UPDATE=1" in lines[0]
