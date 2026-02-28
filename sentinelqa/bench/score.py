from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Set


def load_expectations(fixtures_dir: Path) -> dict:
    path = fixtures_dir / "expectations.json"
    data = json.loads(path.read_text())
    data.setdefault("event_ids", [])
    return data


def load_produced(artifacts_dir: Path, run_id: str) -> Set[str]:
    events_path = artifacts_dir / "runs" / run_id / "events.json"
    events = json.loads(events_path.read_text())
    return {ev.get("event_id") for ev in events if ev.get("event_id")}


def compute_prf(expected_ids: Iterable[str], produced_ids: Iterable[str]) -> dict:
    expected = set(expected_ids)
    produced = set(produced_ids)
    tp = len(expected & produced)
    fp = len(produced - expected)
    fn = len(expected - produced)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "missing": sorted(expected - produced),
        "unexpected": sorted(produced - expected),
    }

