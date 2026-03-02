import json
import os
from pathlib import Path

from app.pipeline import run_pipeline


def test_tickets_written_but_events_from_fixtures(tmp_path, monkeypatch):
    artifacts_dir = tmp_path / "artifacts"
    monkeypatch.setenv("ARTIFACTS_DIR", str(artifacts_dir))
    monkeypatch.setenv("TICKET_SOURCE", "fixtures")
    monkeypatch.delenv("TICKETS_CONSUME", raising=False)
    monkeypatch.setattr(run_pipeline.settings, "artifacts_dir", str(artifacts_dir))

    # fixtures for events
    fixtures_dir = tmp_path / "fixtures" / "tickets"
    fixtures_dir.mkdir(parents=True)
    (fixtures_dir / "sample1.json").write_text(
        json.dumps(
            {
                "customer": "Acme",
                "subject": "Fixture Subject",
                "body": "Fixture Body",
                "created_at": "2026-02-24T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    # fixtures for tickets (unordered ids to verify sort)
    tickets_path = tmp_path / "fixtures" / "zendesk" / "v1" / "tickets_v1.json"
    tickets_path.parent.mkdir(parents=True, exist_ok=True)
    tickets_payload = {
        "version": 1,
        "tickets": [
            {
                "id": "b",
                "subject": "Second",
                "description": "Second desc",
                "created_at": "2026-02-01T00:00:00Z",
                "updated_at": "2026-02-01T00:00:00Z",
                "tags": [],
                "status": "open",
            },
            {
                "id": "a",
                "subject": "First",
                "description": "First desc",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "tags": [],
                "status": "open",
            },
        ],
    }
    tickets_path.write_text(json.dumps(tickets_payload), encoding="utf-8")

    # force FixtureTicketSource to read our temp path
    from app.sources.tickets import FixtureTicketSource as _FTS
    monkeypatch.setenv("TICKET_SOURCE", "fixtures")
    monkeypatch.setenv("TICKET_LIMIT", "10")
    monkeypatch.setattr(run_pipeline, "FixtureTicketSource", lambda *_args, **_kwargs: _FTS(tickets_path))

    run_id = "run1"
    run_pipeline.run_pipeline(run_id, {"fixtures_dir": str(fixtures_dir)})

    run_dir = artifacts_dir / "runs" / run_id
    tickets_file = run_dir / "tickets.json"
    events_file = run_dir / "events.json"

    assert tickets_file.exists()
    tickets = json.loads(tickets_file.read_text())
    assert [t["id"] for t in tickets["tickets"]] == ["a", "b"]  # sorted

    events = json.loads(events_file.read_text())
    # Should reflect fixture events, not ticket count
    assert len(events) == 1
    assert events[0]["normalized"]["subject"] == "Fixture Subject"
