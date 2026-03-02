import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from app.sources.tickets import FixtureTicketSource
from app.cli.zendesk_record import sanitize_ticket_record


def _write_fixture(path: Path, tickets: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "tickets": tickets}
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_fixture_ticket_source_returns_sorted(tmp_path: Path):
    fixture_path = tmp_path / "tickets_v1.json"
    _write_fixture(
        fixture_path,
        [
            {"id": "b", "subject": "b", "description": "", "created_at": "1", "updated_at": "1", "tags": [], "status": "open"},
            {"id": "a", "subject": "a", "description": "", "created_at": "1", "updated_at": "1", "tags": [], "status": "open"},
        ],
    )
    src = FixtureTicketSource(fixture_path)
    tickets = src.fetch(limit=10)
    assert [t.id for t in tickets] == ["a", "b"]


def test_fixture_missing_file_raises(tmp_path: Path):
    src = FixtureTicketSource(tmp_path / "missing.json")
    with pytest.raises(ValueError):
        src.fetch(limit=1)


def test_sanitizer_removes_pii_fields():
    raw = {
        "id": 1,
        "subject": "hello",
        "description": "desc",
        "created_at": "now",
        "updated_at": "later",
        "tags": ["t1"],
        "status": "open",
        "requester": {"name": "Secret", "email": "secret@example.com"},
        "attachments": [{"url": "http://example.com"}],
    }
    sanitized = sanitize_ticket_record(raw)
    assert set(sanitized.keys()) == {"id", "subject", "description", "created_at", "updated_at", "tags", "status"}
    assert "requester" not in sanitized and "attachments" not in sanitized


def test_tickets_schema_validation_passes(tmp_path: Path):
    schema_path = Path("sentinelqa/schemas/tickets_v1.json")
    schema = json.loads(schema_path.read_text())
    payload = {
        "version": 1,
        "tickets": [
            {
                "id": "123",
                "subject": "Test",
                "description": "Body",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "tags": ["a"],
                "status": "open",
            }
        ],
    }
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    assert errors == []
