from __future__ import annotations

import os
from pathlib import Path

import pytest

# Lazily import alembic/sqlalchemy; skip tests if not installed in env.
command = pytest.importorskip("alembic.command")
autogen_api = pytest.importorskip("alembic.autogenerate.api")
Config = pytest.importorskip("alembic.config").Config
MigrationContext = pytest.importorskip("alembic.runtime.migration").MigrationContext
ScriptDirectory = pytest.importorskip("alembic.script").ScriptDirectory
sqla = pytest.importorskip("sqlalchemy")
create_engine = sqla.create_engine
inspect = sqla.inspect


REPO_ROOT = Path(__file__).resolve().parents[1]


def _database_url() -> str | None:
    # Prefer already-set env; fallback to .env if present for local runs.
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip()
    return None


def _alembic_config(db_url: str) -> Config:
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def _engine(db_url: str):
    return create_engine(db_url, pool_pre_ping=True)


def test_migrations_apply_and_head_matches_db():
    db_url = _database_url()
    if not db_url:
        pytest.skip("DATABASE_URL not set; skipping migration tests")
    if not db_url.startswith("postgresql"):
        pytest.skip("DATABASE_URL is not postgres; skipping migration tests")
    engine = _engine(db_url)
    cfg = _alembic_config(db_url)

    # Upgrade to the latest revision (idempotent).
    command.upgrade(cfg, "head")

    script = ScriptDirectory.from_config(cfg)
    head_revision = script.get_current_head()

    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        current_revision = context.get_current_revision()

        inspector = inspect(conn)
        assert "alembic_version" in inspector.get_table_names()

    assert current_revision == head_revision


def test_metadata_matches_database_schema():
    db_url = _database_url()
    if not db_url:
        pytest.skip("DATABASE_URL not set; skipping migration tests")
    if not db_url.startswith("postgresql"):
        pytest.skip("DATABASE_URL is not postgres; skipping migration tests")
    engine = _engine(db_url)
    cfg = _alembic_config(db_url)
    command.upgrade(cfg, "head")

    # Import models lazily after DATABASE_URL is confirmed to avoid Settings validation errors.
    from app.core.models import Base

    with engine.connect() as conn:
        context = MigrationContext.configure(
            connection=conn,
            opts={
                "compare_type": True,
                "compare_server_default": True,
                "include_object": lambda obj, name, type_, reflected, compare_to: (
                    False if type_ == "table" and name == "alembic_version" else True
                ),
            },
        )
        diff = autogen_api.compare_metadata(context, Base.metadata)

    assert diff == [], f"Detected schema drift: {diff}"
