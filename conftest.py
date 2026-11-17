from __future__ import annotations

import os
import socket
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import TypedDict

import pytest
import requests

ROOT = Path(__file__).resolve().parent


class Session(TypedDict):
    client: requests.Session
    proxy: str
    sapodilla: str
    compose: str


def _wait(url: str) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2).close()
            return
        except Exception:
            time.sleep(0.5)
    raise TimeoutError(url)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _compose(env: dict[str, str], *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", *args], cwd=ROOT, capture_output=True, text=True, timeout=300, env=env
    )


@pytest.fixture(scope="session")
def session():
    ports = {name: _free_port() for name in ("LISTEN_PORT", "SAPODILLA_PORT", "UPSTREAM_PORT")}
    env = os.environ | {name: str(port) for name, port in ports.items()}
    client = requests.Session()
    deps: Session = {
        "client": client,
        "proxy": f"http://127.0.0.1:{ports['LISTEN_PORT']}",
        "sapodilla": f"http://127.0.0.1:{ports['SAPODILLA_PORT']}",
        "compose": (ROOT / "compose.yaml").read_text(),
    }
    try:
        result = _compose(env, "up", "-d", "--build")
        assert result.returncode == 0, result.stderr
        _wait(f"{deps['proxy']}/api/ping")
        yield deps
    finally:
        client.close()
        _compose(env, "down", "-v", "-t", "3")


@pytest.fixture
def usage_before(session: Session) -> int:
    return session["client"].get(f"{session['sapodilla']}/api/usage", timeout=5).json()["total"]
