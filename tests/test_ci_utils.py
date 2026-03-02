import socket
import threading
from pathlib import Path

import pytest

from sentinelqa.ci.wait_tcp import wait_tcp
from sentinelqa.ci.write_env import _deterministic_env_content, write_env


def _start_dummy_tcp_server(host: str = "127.0.0.1") -> tuple[int, callable]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, 0))
    except PermissionError as exc:  # some sandboxes block bind
        sock.close()
        pytest.skip(f"Skipping TCP bind due to permission error: {exc}")
    sock.listen()
    sock.settimeout(0.1)
    port = sock.getsockname()[1]

    stop_event = threading.Event()

    def _serve():
        try:
            while not stop_event.is_set():
                try:
                    conn, _ = sock.accept()
                except socket.timeout:
                    continue
                conn.close()
        finally:
            sock.close()

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    
    def shutdown() -> None:
        stop_event.set()
        thread.join(timeout=1)

    return port, shutdown


def test_wait_tcp_succeeds_with_reachable_port():
    port, shutdown = _start_dummy_tcp_server()
    try:
        wait_tcp("127.0.0.1", port, timeout=2, interval=0.1)
    finally:
        shutdown()


def test_wait_tcp_times_out_on_unreachable_port():
    # Allocate an ephemeral free port then close it so nothing listens there.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
    except PermissionError as exc:
        pytest.skip(f"Skipping unreachable-port test due to permission error: {exc}")

    with pytest.raises(RuntimeError):
        wait_tcp("127.0.0.1", port, timeout=0.5, interval=0.05)


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


def test_write_env_ignores_empty_optionals(tmp_path: Path):
    env = {
        "ARTIFACTS_DIR": "",
        "RQ_QUEUE_NAME": "   ",
    }
    out = tmp_path / ".env"
    write_env(out, env)
    content = out.read_text().splitlines()
    assert content == [
        "DATABASE_URL=postgresql+psycopg://signalforge:signalforge@postgres:5432/signalforge",
        "REDIS_URL=redis://redis:6379/0",
    ]


def test_write_env_falls_back_on_empty_required(tmp_path: Path):
    env = {
        "DATABASE_URL": "",
    }
    out = tmp_path / ".env"
    write_env(out, env)
    content = out.read_text().splitlines()
    assert content[0] == "DATABASE_URL=postgresql+psycopg://signalforge:signalforge@postgres:5432/signalforge"
