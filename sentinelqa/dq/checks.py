from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


class EventFixture(BaseModel):
    model_config = ConfigDict(extra="ignore")

    subject: str
    body: str
    created_at: datetime


def validate_fixtures(fixtures_dir: Path | str = Path("fixtures/tickets")) -> tuple[bool, str | None]:
    fixtures_path = Path(fixtures_dir)
    errors: list[str] = []

    files = sorted(fixtures_path.glob("*.json"))
    if not files:
        errors.append("no fixture files found in fixtures/tickets")

    for file in files:
        try:
            data = json.loads(file.read_text())
        except json.JSONDecodeError as exc:
            errors.append(f"{file.name}: invalid json ({exc})")
            continue

        try:
            EventFixture.model_validate(data)
        except ValidationError as exc:
            errors.append(f"{file.name}: {exc.errors()}")

    if errors:
        return False, "; ".join(errors)
    return True, None


def _require_keys(data: dict, keys: Iterable[str]) -> list[str]:
    missing = []
    for key in keys:
        if key not in data:
            missing.append(key)
    return missing


def check_artifact_invariants(run_dir: Path, run_id: str) -> tuple[bool, str | None]:
    events_path = run_dir / "events.json"
    metrics_path = run_dir / "metrics.json"

    if not events_path.exists():
        return False, f"missing {events_path}"
    if not metrics_path.exists():
        return False, f"missing {metrics_path}"

    try:
        events = json.loads(events_path.read_text())
    except json.JSONDecodeError as exc:
        return False, f"events.json invalid json ({exc})"

    if not isinstance(events, list) or len(events) == 0:
        return False, "events.json must be a non-empty list"

    seen_ids: set[str] = set()
    for event in events:
        event_id = event.get("event_id")
        if event_id is None:
            return False, "event missing event_id"
        if event_id in seen_ids:
            return False, f"duplicate event_id {event_id}"
        seen_ids.add(event_id)

    try:
        metrics = json.loads(metrics_path.read_text())
    except json.JSONDecodeError as exc:
        return False, f"metrics.json invalid json ({exc})"

    if metrics.get("run_id") != run_id:
        return False, f"metrics.run_id ({metrics.get('run_id')}) != {run_id}"

    required_keys = ["events", "clusters", "alerts_sent", "latency_ms"]
    missing = _require_keys(metrics, required_keys)
    if missing:
        return False, f"metrics missing keys: {', '.join(missing)}"

    return True, None


def check_db_invariant(run_id: str) -> tuple[str, str | None]:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return "skip", "DATABASE_URL not set"
    if not db_url.startswith("postgresql"):
        return "skip", "DATABASE_URL is not postgres; skipping DB check"

    engine = create_engine(db_url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            total_runs = conn.execute(text("SELECT count(*) FROM runs")).scalar_one()
            if total_runs == 0:
                return "skip", "runs table empty; persistence not yet enabled"
            row = conn.execute(text("SELECT status FROM runs WHERE run_id = :run_id"), {"run_id": run_id}).fetchone()
            if row is None:
                return "fail", "run row not found"
            status = row[0]
            if status != "succeeded":
                return "fail", f"run status is {status}"
    except SQLAlchemyError as exc:
        return "fail", f"db error: {exc}"

    return "pass", None
