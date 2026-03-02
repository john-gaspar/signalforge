import json
import os
import time
from pathlib import Path

from app.core.config import settings
from app.pipeline.stages_stub import load_fixture_events, cluster_stub, summarize_stub, alert_stub
from app.sources.tickets import FixtureTicketSource, ZendeskTicketSource, Ticket

def _ticket_limit() -> int:
    try:
        return int(os.getenv("TICKET_LIMIT", "100"))
    except ValueError:
        return 100


def _select_ticket_source(config: dict):
    source_type = os.getenv("TICKET_SOURCE", "fixtures").lower()
    fixtures_path_env = os.getenv("TICKETS_FIXTURES_PATH")
    fixtures_path = Path(fixtures_path_env) if fixtures_path_env else Path("fixtures/zendesk/v1/tickets_v1.json")
    if source_type == "zendesk":
        return ZendeskTicketSource()
    return FixtureTicketSource(fixtures_path)


def _write_tickets_artifact(run_dir: Path, tickets: list[Ticket]) -> None:
    payload = {
        "version": 1,
        "tickets": [
            {
                "id": t.id,
                "subject": t.subject,
                "description": t.description,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
                "tags": t.tags,
                "status": t.status,
            }
            for t in tickets
        ],
    }
    (run_dir / "tickets.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _tickets_to_raw_events(tickets: list[Ticket]) -> list[dict]:
    return [
        {
            "customer": "unknown",
            "subject": t.subject,
            "body": t.description,
            "created_at": t.created_at,
            "raw_file": "tickets.json",
        }
        for t in tickets
    ]


def run_pipeline(run_id: str, config: dict) -> dict:
    """
    Deterministic pipeline runner:
    - reads fixtures
    - runs stub embed/cluster/summarize/alert
    - writes artifacts to artifacts/runs/<run_id>/
    """
    run_dir = Path(settings.artifacts_dir) / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()

    ticket_source = _select_ticket_source(config)
    tickets = ticket_source.fetch(limit=_ticket_limit())
    _write_tickets_artifact(run_dir, tickets)

    if os.getenv("TICKETS_CONSUME") == "1":
        events = load_fixture_events(config=config, run_dir=run_dir, raw_tickets=_tickets_to_raw_events(tickets))
    else:
        events = load_fixture_events(config=config, run_dir=run_dir)
    clusters = cluster_stub(events=events, run_dir=run_dir)
    summary = summarize_stub(clusters=clusters, run_dir=run_dir)
    alert = alert_stub(summary=summary, run_dir=run_dir)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    metrics = {
        "run_id": run_id,
        "events": len(events),
        "clusters": len(clusters),
        "alerts_sent": 1 if alert.get("decision") == "sent" else 0,
        "latency_ms": elapsed_ms,
        "cost_usd_est": 0.0,  # fill later
    }

    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    return metrics
