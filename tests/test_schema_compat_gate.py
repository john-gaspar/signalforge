from pathlib import Path
import json

from sentinelqa.gates.gate_schema_compat import compare_schema


def test_non_breaking_optional_added(tmp_path: Path):
    base = {"required": ["a"], "properties": {"a": {"type": "string"}}}
    cur = {"required": ["a"], "properties": {"a": {"type": "string"}, "b": {"type": "number"}}}
    assert compare_schema(cur, base) == []


def test_breaking_required_removed(tmp_path: Path):
    base = {"required": ["a", "b"], "properties": {"a": {"type": "string"}, "b": {"type": "string"}}}
    cur = {"required": ["a"], "properties": {"a": {"type": "string"}, "b": {"type": "string"}}}
    errs = compare_schema(cur, base)
    assert any("required removed" in e for e in errs)


def test_breaking_type_change(tmp_path: Path):
    base = {"required": ["a"], "properties": {"a": {"type": "string"}}}
    cur = {"required": ["a"], "properties": {"a": {"type": "number"}}}
    errs = compare_schema(cur, base)
    assert any("type change" in e for e in errs)
