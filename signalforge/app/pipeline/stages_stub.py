from typing import Any, Iterable


def stage_ingest(ticket: Any) -> Any:
    """Pretend to ingest data."""
    ticket = dict(ticket) if isinstance(ticket, dict) else {"ticket": ticket}
    ticket["ingested"] = True
    return ticket


def stage_enrich(ticket: Any) -> Any:
    """Stub enrichment step."""
    ticket["enriched"] = True
    return ticket


def stage_score(ticket: Any) -> Any:
    """Attach a placeholder quality score."""
    ticket["score"] = 0.5
    return ticket


DEFAULT_STAGES: Iterable = (stage_ingest, stage_enrich, stage_score)
