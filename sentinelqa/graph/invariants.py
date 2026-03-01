from __future__ import annotations

from typing import Dict, List, Set, Tuple

from neo4j import Driver


def _fetch_set(session, query: str, key: str, **params) -> Set[str]:
    result = session.run(query, **params)
    values = set()
    for record in result:
        val = record.get(key)
        if isinstance(val, list):
            values.update(str(v) for v in val)
        elif val is not None:
            values.add(str(val))
    return values


def _fetch_int(session, query: str, **params) -> int:
    record = session.run(query, **params).single()
    return int(record[0]) if record else 0


def check_invariants(driver: Driver, run_id: str, expected: Dict[str, Dict[str, any]]) -> List[str]:
    issues: List[str] = []
    expected_events = expected["events"]["ids"]
    expected_event_count = expected["events"]["count"]
    expected_clusters = expected["clusters"]["ids"]
    expected_cluster_count = expected["clusters"]["count"]
    expected_cluster_edges: List[Tuple[str, str]] = expected["clusters"]["edges"]

    with driver.session() as session:
        run_count = _fetch_int(session, "MATCH (r:Run {run_id:$run_id}) RETURN count(r)", run_id=run_id)
        if run_count != 1:
            issues.append(f"Run node count mismatch: expected 1 got {run_count}")

        event_rel_count = _fetch_int(
            session, "MATCH (:Run {run_id:$run_id})-[:HAS_EVENT]->(e:Event) RETURN count(e)", run_id=run_id
        )
        if event_rel_count != expected_event_count:
            issues.append(f"HAS_EVENT count mismatch: expected {expected_event_count} got {event_rel_count}")

        graph_event_ids = _fetch_set(
            session,
            "MATCH (:Run {run_id:$run_id})-[:HAS_EVENT]->(e:Event) RETURN collect(e.event_id) AS ids",
            run_id=run_id,
            key="ids",
        )
        missing_events = expected_events - graph_event_ids
        extra_events = graph_event_ids - expected_events
        if missing_events:
            issues.append(f"Missing events in graph: {sorted(missing_events)}")
        if extra_events:
            issues.append(f"Unexpected events in graph: {sorted(extra_events)}")

        if expected_cluster_count > 0:
            cluster_rel_count = _fetch_int(
                session,
                "MATCH (:Run {run_id:$run_id})-[:HAS_CLUSTER]->(c:Cluster) RETURN count(c)",
                run_id=run_id,
            )
            if cluster_rel_count != expected_cluster_count:
                issues.append(f"HAS_CLUSTER count mismatch: expected {expected_cluster_count} got {cluster_rel_count}")

            graph_cluster_ids = _fetch_set(
                session,
                "MATCH (:Run {run_id:$run_id})-[:HAS_CLUSTER]->(c:Cluster) RETURN collect(c.cluster_id) AS ids",
                run_id=run_id,
                key="ids",
            )
            missing_clusters = expected_clusters - graph_cluster_ids
            extra_clusters = graph_cluster_ids - expected_clusters
            if missing_clusters:
                issues.append(f"Missing clusters in graph: {sorted(missing_clusters)}")
            if extra_clusters:
                issues.append(f"Unexpected clusters in graph: {sorted(extra_clusters)}")

            invalid_edges = _fetch_int(
                session,
                """
                MATCH (:Run {run_id:$run_id})-[:HAS_CLUSTER]->(c:Cluster)-[:CONTAINS_EVENT]->(e:Event)
                WHERE NOT (:Run {run_id:$run_id})-[:HAS_EVENT]->(e)
                RETURN count(*)""",
                run_id=run_id,
            )
            if invalid_edges:
                issues.append(f"{invalid_edges} cluster->event edges reference events not linked to run")

            # check cluster member coverage
            if expected_cluster_edges:
                graph_edges = _fetch_set(
                    session,
                    """
                    MATCH (:Run {run_id:$run_id})-[:HAS_CLUSTER]->(c:Cluster)-[:CONTAINS_EVENT]->(e:Event)
                    RETURN collect(c.cluster_id + '::' + e.event_id) AS edges
                    """,
                    run_id=run_id,
                    key="edges",
                )
                expected_edge_keys = {f"{cid}::{eid}" for cid, eid in expected_cluster_edges}
                missing_edge = expected_edge_keys - graph_edges
                extra_edge = graph_edges - expected_edge_keys
                if missing_edge:
                    issues.append(f"Missing cluster edges: {sorted(missing_edge)}")
                if extra_edge:
                    issues.append(f"Unexpected cluster edges: {sorted(extra_edge)}")

        # Orphans: events attached to run must have HAS_EVENT rel; covered by set diff.

    return issues
