import json
from pathlib import Path
from app.core.ids import stable_json, sha256_hex

def load_fixture_events(config: dict, run_dir: Path, raw_tickets: list[dict] | None = None) -> list[dict]:
    fixtures_dir = Path(config.get("fixtures_dir", "fixtures/tickets"))
    events = []

    if raw_tickets is None:
        files = sorted(fixtures_dir.glob("*.json"))  # sorting = determinism
        raw_entries = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    else:
        raw_entries = raw_tickets

    for raw in raw_entries:
        normalized = normalize_ticket(raw)
        event_id = sha256_hex(stable_json(normalized))[:32]
        raw_ref = str(raw.get("raw_file")) if isinstance(raw, dict) and raw.get("raw_file") else str(fixtures_dir)
        ev = {"event_id": event_id, "source": "fixture", "normalized": normalized, "raw_file": raw_ref}
        events.append(ev)

    (run_dir / "events.json").write_text(json.dumps(events, indent=2, sort_keys=True), encoding="utf-8")
    return events

def normalize_ticket(raw: dict) -> dict:
    # Minimal normalization; expand later (strip signatures, etc.)
    return {
        "customer": raw.get("customer", "unknown"),
        "subject": (raw.get("subject") or "").strip(),
        "body": (raw.get("body") or "").strip(),
        "created_at": raw.get("created_at"),
    }

def cluster_stub(events: list[dict], run_dir: Path) -> list[dict]:
    # Deterministic trivial clustering by subject hash prefix (placeholder)
    clusters = {}
    for ev in events:
        key = sha256_hex(ev["normalized"]["subject"])[:8]
        clusters.setdefault(key, []).append(ev["event_id"])

    out = [{"cluster_id": k, "members": v} for k, v in sorted(clusters.items())]
    (run_dir / "clusters.json").write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    return out

def summarize_stub(clusters: list[dict], run_dir: Path) -> dict:
    # Deterministic template summary
    summary = {
        "issue": "Potential incident detected",
        "cluster_count": len(clusters),
        "evidence": [{"cluster_id": c["cluster_id"], "members": c["members"][:3]} for c in clusters],
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary

def alert_stub(summary: dict, run_dir: Path) -> dict:
    decision = "sent" if summary["cluster_count"] >= 1 else "suppressed"
    payload = {
        "decision": decision,
        "channel": "#alerts",
        "text": f"{summary['issue']} | clusters={summary['cluster_count']}",
    }
    (run_dir / "alert.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload
