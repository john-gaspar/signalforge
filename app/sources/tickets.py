from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List

import requests


@dataclass(frozen=True)
class Ticket:
    id: str
    subject: str
    description: str
    created_at: str
    updated_at: str
    tags: list[str]
    status: str


class TicketSource(ABC):
    @abstractmethod
    def fetch(self, limit: int) -> List[Ticket]:
        ...


def _resolve_fixture_path(path: Path | None) -> Path:
    if path is None:
        return Path("fixtures/zendesk/v1/tickets_v1.json")
    if path.is_dir():
        return path / "tickets_v1.json"
    return path


class FixtureTicketSource(TicketSource):
    def __init__(self, path: Path | None = None):
        self.path = _resolve_fixture_path(path or Path("fixtures/zendesk/v1/tickets_v1.json"))

    def fetch(self, limit: int) -> List[Ticket]:
        if not self.path.exists():
            raise ValueError(f"fixture file missing at {self.path}")
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"fixture file invalid json: {exc}") from exc

        if not isinstance(payload, dict) or "tickets" not in payload:
            raise ValueError("fixture payload must contain 'tickets' array")
        tickets = payload.get("tickets")
        if not isinstance(tickets, list):
            raise ValueError("fixture 'tickets' must be a list")

        parsed: List[Ticket] = []
        for entry in tickets:
            if not isinstance(entry, dict):
                raise ValueError("fixture ticket entry is not an object")
            try:
                parsed.append(
                    Ticket(
                        id=str(entry["id"]),
                        subject=str(entry["subject"]),
                        description=str(entry["description"]),
                        created_at=str(entry["created_at"]),
                        updated_at=str(entry["updated_at"]),
                        tags=[str(t) for t in entry.get("tags", [])],
                        status=str(entry["status"]),
                    )
                )
            except KeyError as exc:
                raise ValueError(f"fixture ticket missing field {exc}") from exc

        parsed = sorted(parsed, key=lambda t: t.id)
        return parsed[:limit]


class ZendeskTicketSource(TicketSource):
    def __init__(self, subdomain: str | None = None, email: str | None = None, api_token: str | None = None):
        self.subdomain = subdomain or os.getenv("ZENDESK_SUBDOMAIN")
        self.email = email or os.getenv("ZENDESK_EMAIL")
        self.api_token = api_token or os.getenv("ZENDESK_API_TOKEN")

        if not (self.subdomain and self.email and self.api_token):
            raise RuntimeError("Zendesk credentials missing; set ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_API_TOKEN")

    def _sanitize(self, raw: dict) -> Ticket:
        return Ticket(
            id=str(raw.get("id", "")),
            subject=str(raw.get("subject", "")),
            description=str(raw.get("description", "")),
            created_at=str(raw.get("created_at", "")),
            updated_at=str(raw.get("updated_at", "")),
            tags=[str(t) for t in (raw.get("tags") or [])],
            status=str(raw.get("status", "")),
        )

    def fetch(self, limit: int) -> List[Ticket]:
        url = f"https://{self.subdomain}.zendesk.com/api/v2/search.json"
        params = {"query": "type:ticket", "sort_by": "updated_at", "sort_order": "desc", "page[size]": limit}
        resp = requests.get(url, params=params, auth=(f"{self.email}/token", self.api_token), timeout=10)
        resp.raise_for_status()
        body = resp.json()
        results = body.get("results") or []
        tickets = [self._sanitize(r) for r in results[:limit]]
        return tickets
