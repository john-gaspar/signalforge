from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://signalforge:signalforge@localhost:5432/signalforge")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.api import main


def test_health_ok():
    resp = main.health()
    assert resp == {"status": "ok"}
