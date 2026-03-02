from sentinelqa.ci.check_baseline_changes import evaluate_changed_paths


def test_no_changes_ok():
    ok, lines = evaluate_changed_paths([], allow=False)
    assert ok
    assert "[OK]" in lines[0]
    assert "no baseline" in lines[0]


def test_blocks_baseline_change_without_env():
    changed = ["sentinelqa/baselines/foo.json", "other/file.py"]
    ok, lines = evaluate_changed_paths(changed, allow=False)
    assert not ok
    assert lines[0].startswith("[FAIL]")
    assert "foo.json" in "\n".join(lines)


def test_blocks_schema_change_without_env():
    changed = ["sentinelqa/schemas/events_v1.json"]
    ok, lines = evaluate_changed_paths(changed, allow=False)
    assert not ok
    assert "events_v1.json" in "\n".join(lines)


def test_allows_contract_changes_without_flag():
    changed = ["sentinelqa/contracts/contracts_index.json"]
    ok, lines = evaluate_changed_paths(changed, allow=False)
    assert ok
    assert "contracts_index.json" not in "\n".join(lines)


def test_allows_protected_changes_with_env():
    changed = ["sentinelqa/baselines/foo.json", "sentinelqa/schemas/events_v1.json"]
    ok, lines = evaluate_changed_paths(changed, allow=True)
    assert ok
    assert lines[0].startswith("[OK]")
    assert "foo.json" in "\n".join(lines)
    assert "events_v1.json" in "\n".join(lines)
