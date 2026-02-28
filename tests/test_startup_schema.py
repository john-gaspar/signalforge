from __future__ import annotations

import sentinelqa.ci.startup as startup


def test_ensure_schema_calls_wait_and_upgrade(monkeypatch):
    called = {"wait": False, "upgrade": False}

    def fake_wait(host, port, timeout, interval=1.0):
        called["wait"] = (host, port, timeout)

    def fake_upgrade(env):
        called["upgrade"] = env.get("DATABASE_URL")

    monkeypatch.setattr(startup, "wait_for_host", fake_wait)
    monkeypatch.setattr(startup, "run_alembic_upgrade", fake_upgrade)

    startup.ensure_schema("postgresql+psycopg://u:p@db:5432/name", wait_timeout=42)

    assert called["wait"] == ("db", 5432, 42)
    assert called["upgrade"].startswith("postgresql+psycopg://u:p@db:5432")
