from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from app.core.ids import sha256_hex, stable_json
from app.sources.tickets import ZendeskTicketSource, Ticket


ALLOWED_FIELDS = {"id", "subject", "description", "created_at", "updated_at", "tags", "status"}


def sanitize_ticket_record(raw: dict) -> dict:
    """Return a Ticket-shaped dict, dropping PII/unused fields."""
    sanitized = {
        "id": str(raw.get("id", "")),
        "subject": raw.get("subject", "") or "",
        "description": raw.get("description", "") or "",
        "created_at": raw.get("created_at", "") or "",
        "updated_at": raw.get("updated_at", "") or "",
        "tags": [str(t) for t in (raw.get("tags") or [])],
        "status": raw.get("status", "") or "",
    }
    return {k: sanitized[k] for k in ALLOWED_FIELDS}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _to_ticket(raw: dict) -> Ticket:
    clean = sanitize_ticket_record(raw)
    return Ticket(
        id=str(clean["id"]),
        subject=str(clean["subject"]),
        description=str(clean["description"]),
        created_at=str(clean["created_at"]),
        updated_at=str(clean["updated_at"]),
        tags=[str(t) for t in clean.get("tags", [])],
        status=str(clean["status"]),
    )


def _compute_manifest_sha(payload: dict) -> str:
    return sha256_hex(stable_json(payload))


def main() -> None:
    parser = argparse.ArgumentParser(description="Record Zendesk tickets into fixtures for deterministic replay")
    parser.add_argument("--out", required=True, help="Output directory for fixtures (e.g., fixtures/zendesk/v1)")
    parser.add_argument("--limit", type=int, default=50, help="Number of tickets to fetch")
    args = parser.parse_args()

    out_dir = Path(args.out)
    tickets_path = out_dir / "tickets_v1.json"
    manifest_path = out_dir / "manifest.json"

    source = ZendeskTicketSource()
    raw_tickets = source.fetch(limit=args.limit)
    sanitized = [asdict(_to_ticket(asdict(t))) if isinstance(t, Ticket) else asdict(_to_ticket(t)) for t in raw_tickets]

    payload = {"version": 1, "tickets": sanitized}
    _write_json(tickets_path, payload)

    manifest = {
        "version": 1,
        "sha256": _compute_manifest_sha(payload),
        "count": len(sanitized),
    }
    _write_json(manifest_path, manifest)

    print(f"Wrote {len(sanitized)} tickets to {tickets_path}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
