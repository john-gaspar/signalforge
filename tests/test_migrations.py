from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.autogenerate import api as autogen_api
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from app.core.db import engine
from app.core.models import Base


REPO_ROOT = Path(__file__).resolve().parents[1]


def _alembic_config() -> Config:
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", str(engine.url))
    return cfg


def test_migrations_apply_and_head_matches_db():
    cfg = _alembic_config()

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
    cfg = _alembic_config()
    command.upgrade(cfg, "head")

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
