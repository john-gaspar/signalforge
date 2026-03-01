from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from neo4j import Driver

ALLOWED_EVENT_FIELDS = ("event_id", "event_type", "severity", "source")
ALLOWED_CLUSTER_FIELDS = ("cluster_id",)
ALLOWED_ALERT_FIELDS = ("alert_id",)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def load_artifacts(run_dir: Path) -> Dict[str, Any]:
    """Load artifacts for a run and project only stable fields."""
    events_path = run_dir / "events.json"
    clusters_path = run_dir / "clusters.json"
    alert_path = run_dir / "alert.json"

    events: List[Dict[str, Any]] = []
    if events_path.exists():
        raw_events: Sequence[Dict[str, Any]] = _read_json(events_path)
        for e in raw_events:
            if "event_id" not in e:
                continue
            projected = {
                "event_id": e.get("event_id"),
                "event_type": e.get("event_type") or e.get("type") or e.get("normalized", {}).get("event_type"),
                "severity": e.get("severity") or e.get("normalized", {}).get("severity"),
                "source": e.get("source"),
            }
            # remove None values
            projected = {k: v for k, v in projected.items() if v is not None}
            events.append(projected)

    clusters: List[Dict[str, Any]] = []
    if clusters_path.exists():
        raw_clusters: Sequence[Dict[str, Any]] = _read_json(clusters_path)
        for c in raw_clusters:
            cid = c.get("cluster_id")
            if not cid:
                continue
            clusters.append(
                {
                    "cluster_id": cid,
                    "member_event_ids": [mid for mid in c.get("members", []) if mid],
                }
            )

    alerts: List[Dict[str, Any]] = []
    if alert_path.exists():
        alert_obj = _read_json(alert_path)
        alert_id = alert_obj.get("alert_id")
        if alert_id:
            alerts.append({"alert_id": alert_id})

    return {"events": events, "clusters": clusters, "alerts": alerts}


def persist_to_graph(run_id: str, artifacts: Dict[str, Any], driver: Driver) -> None:
    """Idempotently persist run artifacts to Neo4j using MERGE."""
    events: List[Dict[str, Any]] = artifacts.get("events", [])
    clusters: List[Dict[str, Any]] = artifacts.get("clusters", [])
    alerts: List[Dict[str, Any]] = artifacts.get("alerts", [])

    with driver.session() as session:
        session.run("MERGE (r:Run {run_id: $run_id})", run_id=run_id)

        if events:
            session.run(
                """
                UNWIND $events AS e
                MERGE (r:Run {run_id: $run_id})
                MERGE (ev:Event {event_id: e.event_id})
                SET ev += e
                MERGE (r)-[:HAS_EVENT]->(ev)
                """,
                run_id=run_id,
                events=events,
            )

        if clusters:
            session.run(
                """
                UNWIND $clusters AS c
                MERGE (r:Run {run_id: $run_id})
                MERGE (cl:Cluster {cluster_id: c.cluster_id})
                MERGE (r)-[:HAS_CLUSTER]->(cl)
                FOREACH (eid IN c.member_event_ids |
                  MERGE (ev:Event {event_id: eid})
                  MERGE (cl)-[:CONTAINS_EVENT]->(ev)
                )
                """,
                run_id=run_id,
                clusters=clusters,
            )

        if alerts:
            session.run(
                """
                UNWIND $alerts AS a
                MERGE (r:Run {run_id: $run_id})
                MERGE (al:Alert {alert_id: a.alert_id})
                MERGE (r)-[:HAS_ALERT]->(al)
                """,
                run_id=run_id,
                alerts=alerts,
            )


def summarize_expected(artifacts: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "events": {
            "count": len(artifacts.get("events", [])),
            "ids": {e["event_id"] for e in artifacts.get("events", []) if "event_id" in e},
        },
        "clusters": {
            "count": len(artifacts.get("clusters", [])),
            "ids": {c["cluster_id"] for c in artifacts.get("clusters", []) if "cluster_id" in c},
            "edges": [
                (c["cluster_id"], eid)
                for c in artifacts.get("clusters", [])
                for eid in c.get("member_event_ids", [])
            ],
        },
    }
