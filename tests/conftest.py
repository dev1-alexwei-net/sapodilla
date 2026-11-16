"""Session fixtures for the Compose integration tests."""

from __future__ import annotations

import os
import socket
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent


def _wait_http(url: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return
        except Exception:
            time.sleep(0.5)
    raise TimeoutError(f"timed out waiting for {url}")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _compose_env(ports: dict[str, int]) -> dict[str, str]:
    return os.environ | {key: str(value) for key, value in ports.items()}


def _compose(*args: str, env: dict[str, str], timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


@pytest.fixture(scope="session")
def compose_ports() -> dict[str, int]:
    return {name: _free_port() for name in ("LISTEN_PORT", "SIDECAR_PORT", "UPSTREAM_PORT")}


@pytest.fixture(scope="session")
def proxy(compose_ports: dict[str, int]) -> Iterator[str]:
    env = _compose_env(compose_ports)
    result = _compose("up", "-d", "--build", env=env)
    if result.returncode:
        _compose("down", "-v", "-t", "3", env=env)
        raise RuntimeError(f"docker compose up failed:\n{result.stderr}")

    base = f"http://127.0.0.1:{compose_ports['LISTEN_PORT']}"
    _wait_http(f"{base}/api/ping")
    try:
        yield base
    finally:
        _compose("down", "-v", "-t", "3", env=env)


@pytest.fixture
def sidecar_stopped(proxy: str, compose_ports: dict[str, int]) -> Iterator[None]:
    env = _compose_env(compose_ports)
    result = _compose("stop", "sidecar", env=env)
    if result.returncode:
        raise RuntimeError(f"docker compose stop sidecar failed:\n{result.stderr}")
    try:
        yield
    finally:
        result = _compose("start", "sidecar", env=env)
        if result.returncode:
            raise RuntimeError(f"docker compose start sidecar failed:\n{result.stderr}")
        _wait_http(f"http://127.0.0.1:{compose_ports['SIDECAR_PORT']}/api/healthz")


@pytest.fixture(scope="session")
def compose_sidecar(compose_ports: dict[str, int]) -> str:
    return f"http://127.0.0.1:{compose_ports['SIDECAR_PORT']}"
