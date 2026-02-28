from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
from urllib.parse import urlparse
from sqlalchemy import create_engine, text


def wait_for_host(host: str, port: int, timeout: int = 60, interval: float = 1.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(interval)
            try:
                sock.connect((host, port))
                return
            except OSError:
                time.sleep(interval)
    sys.exit(f"Database not reachable at {host}:{port} after {timeout}s")


def run_alembic_upgrade(env: dict[str, str]) -> None:
    cmd = ["alembic", "-c", "alembic.ini", "upgrade", "head"]
    subprocess.run(cmd, check=True, env=env)


def has_alembic_table(db_url: str) -> bool:
    engine = create_engine(db_url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM alembic_version LIMIT 1"))
        return True
    except Exception:
        return False


def ensure_schema(db_url: str, wait_timeout: int = 60) -> None:
    parsed = urlparse(db_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    print(f"Waiting for DB {host}:{port} ...")
    wait_for_host(host, port, timeout=wait_timeout)
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    print("Running alembic upgrade head ...")
    run_alembic_upgrade(env)
    print("Migrations applied.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL"), help="Database URL")
    parser.add_argument("--wait-timeout", type=int, default=60)
    args = parser.parse_args()

    if not args.db_url:
        sys.exit("DATABASE_URL not set; cannot run migrations")

    ensure_schema(args.db_url, wait_timeout=args.wait_timeout)


if __name__ == "__main__":
    main()
