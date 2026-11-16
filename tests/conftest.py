"""Shared fixtures for the ollama-mirror test suite.

Two test layers:
  1. unit       -- Go sidecar started on a random port; tests hit it
                   directly via HTTP.  Uses the ``sidecar`` fixture.
  2. integration -- docker compose stack (generic mock upstream +
                   nginx + sidecar) started via ``docker compose up -d``.
                   Tests hit the nginx front door.  Uses the ``proxy``
                   fixture.

The compose fixture is session-scoped: start once, tear down once.
"""

from __future__ import annotations

import os
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def compose() -> str:
    """Return the Compose file for lightweight configuration assertions."""
    return (REPO_ROOT / "docker-compose.yml").read_text()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wait_http(url: str, timeout: float = 30.0) -> None:
    """Poll `url` until it returns any HTTP status or timeout elapses."""
    deadline = time.monotonic() + timeout
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return
        except Exception as e:  # noqa: BLE001
            last_err = e
        time.sleep(0.5)
    raise TimeoutError(f"timed out waiting for {url}: {last_err}")


def _pick_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _compose(
    *args: str,
    timeout: int = 300,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


# ---------------------------------------------------------------------------
# Sidecar (unit) fixture — session-scoped
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def sidecar() -> str:
    """Build and start the Go sidecar on a random port; yield its base URL."""
    port = _pick_free_port()
    env_addr_port = _pick_free_port()
    bin_path = REPO_ROOT / "build" / "sidecar"
    bin_path.parent.mkdir(parents=True, exist_ok=True)

    build = subprocess.run(
        ["go", "build", "-o", str(bin_path), "."],
        cwd=REPO_ROOT / "sidecar",
        capture_output=True,
        text=True,
    )
    if build.returncode != 0:
        raise RuntimeError(f"go build failed: {build.stderr}")

    env = os.environ.copy()
    # Prove an explicit -addr flag takes precedence over ADDR.
    env["ADDR"] = f"127.0.0.1:{env_addr_port}"
    proc = subprocess.Popen(
        [str(bin_path), "-addr", f"127.0.0.1:{port}"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    _wait_http(f"{base}/api/healthz")
    try:
        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


# ---------------------------------------------------------------------------
# Compose (integration) fixtures — session-scoped
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def compose_ports() -> dict[str, int]:
    """Choose non-default ports to exercise Compose variable overrides."""
    proxy_port = _pick_free_port()
    sidecar_port = _pick_free_port()
    upstream_port = _pick_free_port()
    return {
        "LISTEN_PORT": proxy_port,
        "SIDECAR_PORT": sidecar_port,
        "UPSTREAM_PORT": upstream_port,
    }


@pytest.fixture(scope="session")
def proxy(compose_ports: dict[str, int]) -> str:
    """Start the docker compose stack; yield the NGINX front-door base URL."""
    compose_file = REPO_ROOT / "docker-compose.yml"
    if not compose_file.exists():
        pytest.skip("docker-compose.yml not found")

    compose_env = os.environ.copy()
    compose_env.update({k: str(v) for k, v in compose_ports.items()})

    result = _compose(
        "-f",
        str(compose_file),
        "up",
        "-d",
        "--build",
        env=compose_env,
    )
    if result.returncode != 0:
        _compose("-f", str(compose_file), "down", "--volumes", "-t", "3", env=compose_env)
        raise RuntimeError(
            f"docker compose up failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    base = f"http://127.0.0.1:{compose_ports['LISTEN_PORT']}"
    _wait_http(f"{base}/api/ping")
    try:
        yield base
    finally:
        _compose("-f", str(compose_file), "down", "-v", "-t", "3", env=compose_env)


@pytest.fixture(scope="session")
def compose_sidecar(proxy: str, compose_ports: dict[str, int]) -> str:
    """Return the sidecar API URL after the integration stack is ready."""
    return f"http://127.0.0.1:{compose_ports['SIDECAR_PORT']}"
