from __future__ import annotations

import argparse
import os
from pathlib import Path


DEFAULT_DATABASE_URL = "postgresql+psycopg://signalforge:signalforge@postgres:5432/signalforge"
DEFAULT_REDIS_URL = "redis://redis:6379/0"


def _get_nonempty(env: dict[str, str], key: str) -> str | None:
    val = env.get(key)
    if val is None:
        return None
    if isinstance(val, str) and val.strip() == "":
        return None
    return val


def _deterministic_env_content(env: dict[str, str]) -> str:
    lines: list[str] = []

    db_url = _get_nonempty(env, "DATABASE_URL") or DEFAULT_DATABASE_URL
    redis_url = _get_nonempty(env, "REDIS_URL") or DEFAULT_REDIS_URL

    lines.append(f"DATABASE_URL={db_url}")
    lines.append(f"REDIS_URL={redis_url}")

    artifacts_dir = _get_nonempty(env, "ARTIFACTS_DIR")
    if artifacts_dir is not None:
        lines.append(f"ARTIFACTS_DIR={artifacts_dir}")

    rq_queue = _get_nonempty(env, "RQ_QUEUE_NAME")
    if rq_queue is not None:
        lines.append(f"RQ_QUEUE_NAME={rq_queue}")

    # Trailing newline for POSIX-friendly env files
    return "\n".join(lines) + "\n"


def write_env(path: Path, env: dict[str, str]) -> None:
    content = _deterministic_env_content(env)
    path.write_text(content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Write .env file for docker-compose services")
    parser.add_argument("--path", default=".env")
    args = parser.parse_args()

    env = dict(os.environ)
    write_env(Path(args.path), env)


if __name__ == "__main__":
    main()
