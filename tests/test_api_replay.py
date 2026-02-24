import os
import json
import sys
import types
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient


def make_client(tmp_path: Path):
    # Prepare env for SQLite + artifacts in tempdir
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path/'test.db'}"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["ARTIFACTS_DIR"] = str(tmp_path / "artifacts")
    os.environ["RQ_QUEUE_NAME"] = "signalforge"

    # Provide dummy redis/rq modules if not installed (isolate from system)
    if "redis" not in sys.modules:
        sys.modules["redis"] = types.SimpleNamespace(Redis=Mock())
    if "rq" not in sys.modules:
        sys.modules["rq"] = types.SimpleNamespace(Queue=Mock())

    # Import after env is set
    from app.api.main import app
    from app.core import db as db_module
    db_module.Base.metadata.drop_all(bind=db_module.engine)
    db_module.Base.metadata.create_all(bind=db_module.engine)
    return TestClient(app)


def seed_fixture(tmp_path: Path):
    fixtures_dir = tmp_path / "fixtures" / "tickets"
    fixtures_dir.mkdir(parents=True)
    sample = {
        "customer": "Acme",
        "subject": "Login broken",
        "body": "Users cannot log in",
        "created_at": "2026-02-24T00:00:00Z",
    }
    (fixtures_dir / "sample1.json").write_text(json.dumps(sample), encoding="utf-8")
    return fixtures_dir


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Ensure env and dummy deps are set before importing routes (which import redis)
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path/'test.db'}"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["ARTIFACTS_DIR"] = str(tmp_path / "artifacts")
    os.environ["RQ_QUEUE_NAME"] = "signalforge"
    if "redis" not in sys.modules:
        sys.modules["redis"] = types.SimpleNamespace(Redis=Mock())
    if "rq" not in sys.modules:
        sys.modules["rq"] = types.SimpleNamespace(Queue=Mock())

    fixtures_dir = seed_fixture(tmp_path)

    # Stub Redis / RQ so no external services needed
    import app.api.routes_runs as routes

    fake_queue = Mock()
    fake_job = Mock()
    fake_job.id = "job123"
    fake_queue.enqueue.return_value = fake_job

    fake_redis = Mock()
    fake_redis_queue_ctor = Mock(return_value=fake_queue)

    monkeypatch.setattr(routes, "Redis", Mock(from_url=Mock(return_value=fake_redis)))
    monkeypatch.setattr(routes, "Queue", fake_redis_queue_ctor)

    c = make_client(tmp_path)
    c.fixtures_dir = fixtures_dir  # attach for access in tests
    return c


def test_replay_creates_run_and_is_idempotent(client):
    resp1 = client.post(
        "/runs/replay",
        json={"fixtures_dir": str(client.fixtures_dir), "fault_config": {}},
    )
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert body1["status"] == "queued"
    run_id = body1["run_id"]

    # Duplicate request should be idempotent and return same run_id
    resp2 = client.post(
        "/runs/replay",
        json={"fixtures_dir": str(client.fixtures_dir), "fault_config": {}},
    )
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2.get("idempotent") is True
    assert body2["run_id"] == run_id

    # Fetch run
    resp_get = client.get(f"/runs/{run_id}")
    assert resp_get.status_code == 200
    data = resp_get.json()
    assert data["config"]["fixtures_dir"] == str(client.fixtures_dir)
    assert data["status"] == "queued"  # worker not executed in test
