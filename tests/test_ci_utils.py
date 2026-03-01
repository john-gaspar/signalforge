import os
import socket
import threading
import time
from pathlib import Path

import pytest

from sentinelqa.ci.wait_tcp import wait_tcp
from sentinelqa.ci.write_env import _deterministic_env_content, write_env


def _start_dummy_tcp_server(host: str = "127.0.0.1") -> tuple[threading.Thread, int]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, 0))
    except PermissionError as exc:  # some sandboxes block bind
        sock.close()
        pytest.skip(f"Skipping TCP bind due to permission error: {exc}")
    sock.listen()
    port = sock.getsockname()[1]

    def _serve():
        try:
            conn, _ = sock.accept()
            conn.close()
        finally:
            sock.close()

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    return thread, port


def test_wait_tcp_succeeds_with_reachable_port():
    thread, port = _start_dummy_tcp_server()
    try:
        wait_tcp("127.0.0.1", port, timeout=2, interval=0.1)
    finally:
        # ensure listener thread stops promptly
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            pass
        thread.join(timeout=1)


def test_wait_tcp_times_out_on_unreachable_port():
    # Pick a high port unlikely to be in use; retry logic makes this deterministic enough for CI.
    with pytest.raises(RuntimeError):
        wait_tcp("127.0.0.1", 65530, timeout=1, interval=0.1)


def test_write_env_defaults_and_optionals(tmp_path: Path):
    env = {
        "ARTIFACTS_DIR": "/code/artifacts",
        "RQ_QUEUE_NAME": "signalforge",
    }
    out = tmp_path / ".env"
    write_env(out, env)
    content = out.read_text().splitlines()
    assert content == [
        "DATABASE_URL=postgresql+psycopg://signalforge:signalforge@postgres:5432/signalforge",
        "REDIS_URL=redis://redis:6379/0",
        "ARTIFACTS_DIR=/code/artifacts",
        "RQ_QUEUE_NAME=signalforge",
    ]


def test_write_env_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Ensure ordering and defaults are stable regardless of env ordering
    env = {
        "REDIS_URL": "redis://custom:6379/1",
        "DATABASE_URL": "postgresql+psycopg://u:p@host:5433/db",
    }

    path = tmp_path / ".env"
    write_env(path, env)
    first = path.read_bytes()
    write_env(path, env)
    second = path.read_bytes()
    assert first == second


def test_deterministic_env_content_omits_unset_optionals():
    env = {}
    content = _deterministic_env_content(env)
    lines = content.strip().splitlines()
    assert lines == [
        "DATABASE_URL=postgresql+psycopg://signalforge:signalforge@postgres:5432/signalforge",
        "REDIS_URL=redis://redis:6379/0",
    ]
