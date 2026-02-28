# Graph Database Integration Plan

## Status: Planned (After Alembic)

Prerequisite:
Alembic migrations integrated and `create_all` disabled or guarded.

Graph integration will begin only after relational schema is stable.

---

## Objective

Persist pipeline lineage into a graph database to:

- Validate structural integrity
- Enable relationship-based data quality testing
- Demonstrate graph testing capability
- Support incident lineage queries

---

## Proposed Graph Model (Neo4j default)

Nodes:
- Run
- Event
- Cluster
- Summary
- Alert

Relationships:
- (Run)-[:PRODUCED]->(Event)
- (Event)-[:IN_CLUSTER]->(Cluster)
- (Cluster)-[:HAS_SUMMARY]->(Summary)
- (Cluster)-[:TRIGGERED]->(Alert)

---

## Structural Invariants to Enforce

1. Each Event belongs to exactly 1 Run
2. Each Event belongs to exactly 1 Cluster
3. Each Cluster has at most 1 Summary
4. Alert exists only when cluster threshold crossed
5. Node counts match artifact JSON counts

These invariants will be validated via pytest + graph queries.

---

## Implementation Phases

Phase 1:
- Add Neo4j to docker-compose
- Implement minimal graph writer

Phase 2:
- Add graph integrity tests

Phase 3:
- Integrate graph checks into CI

---

## Interview Framing

"I persist lineage into a graph DB and validate structural invariants automatically in CI, ensuring cross-entity consistency beyond relational constraints."