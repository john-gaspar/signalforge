# CI/CD Evolution Plan

## Current CI

1. Build images
2. Start services (Postgres, Redis)
3. Seed run
4. Run SentinelQA metrics gate
5. Run pytest

---

## Target CI (Post-Alembic)

1. Build images
2. Start services
3. Run migrations
   docker compose run --rm api alembic upgrade head
4. Seed run
5. Data Quality Gate
6. Benchmark Gate
7. Graph Integrity Tests (when implemented)
8. pytest
9. Optional load smoke

---

## CI Philosophy

CI must fail on:

- Schema drift
- Structural corruption
- Metric regression
- Performance regression
- Data quality violation

Quality enforcement must be automatic.
Manual review is not sufficient.