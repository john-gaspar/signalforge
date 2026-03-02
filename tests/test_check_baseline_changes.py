from sentinelqa.ci.check_baseline_changes import evaluate_changed_paths


def test_no_changes_ok():
    ok, lines = evaluate_changed_paths([], allow=False)
    assert ok
    assert "[OK]" in lines[0]
    assert "no protected" in lines[0]


def test_new_schema_allowed_without_flag():
    changed = [("A", "sentinelqa/schemas/new_schema.json")]
    ok, lines = evaluate_changed_paths(changed, allow=False)
    assert ok
    assert "new_schema.json" not in "\n".join(lines)


def test_modified_schema_blocked_without_flag():
    changed = [("M", "sentinelqa/schemas/events_v1.json")]
    ok, lines = evaluate_changed_paths(changed, allow=False)
    assert not ok
    assert "modified" in "\n".join(lines)
    assert "events_v1.json" in "\n".join(lines)


def test_new_contract_blocked_without_flag():
    changed = [("A", "sentinelqa/contracts/new_contract.json")]
    ok, lines = evaluate_changed_paths(changed, allow=False)
    assert not ok
    assert "added-not-allowed" in "\n".join(lines)


def test_all_allowed_with_flag():
    changed = [
        ("A", "sentinelqa/schemas/new_schema.json"),
        ("M", "sentinelqa/schemas/events_v1.json"),
        ("A", "sentinelqa/contracts/new_contract.json"),
        ("M", "sentinelqa/baselines/foo.json"),
    ]
    ok, lines = evaluate_changed_paths(changed, allow=True)
    assert ok
    assert lines[0].startswith("[OK]")
