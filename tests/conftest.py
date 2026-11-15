"""Shared fixtures for the ollama-mirror test suite.

Three test layers:
  1. unit       -- Go sidecar started on a random port; tests hit it
                   directly via HTTP.
  2. integration -- docker compose stack (mock upstream + sidecar + nginx)
                   started via `docker compose up -d`; tests hit the nginx
                   front door (port 8080).
  3. smoke      -- scripts/smoke.sh runs the full cycle headlessly.

The compose fixture is session-scoped: start once, tear down once.
"""

from __future__ import annotations

import subprocess
import time
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Sidecar (unit) fixture
# ---------------------------------------------------------------------------


def _wait_http(url: str, timeout: float = 15.0) -> None:
    """Poll `url` until it returns 200 or timeout elapses."""
    deadline = time.monotonic() + timeout
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception as e:  # noqa: BLE001
            last_err = e
        time.sleep(0.25)
    raise TimeoutError(f"timed out waiting for {url}: {last_err}")


@pytest.fixture(scope="session")
def sidecar_port() -> int:
    """Pick a free port for the sidecar."""
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="session")
def sidecar(sidecar_port: int):
    """Build and start the Go sidecar; yield its base URL; kill on teardown."""
    # Build the binary once (session-scoped)
    bin_path = REPO_ROOT / "build" / "sidecar"
    bin_path.parent.mkdir(parents=True, exist_ok=True)
    build = subprocess.run(
        ["go", "build", "-o", str(bin_path), "."],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if build.returncode != 0:
        raise RuntimeError(f"go build failed: {build.stderr}")

    proc = subprocess.Popen(
        [str(bin_path), "-addr", f"127.0.0.1:{sidecar_port}"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{sidecar_port}"
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
# Compose (integration) fixture
# ---------------------------------------------------------------------------


def _compose(*args: str, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


@pytest.fixture(scope="session")
def compose_stack():
    """Start the docker compose stack (mock upstream + sidecar + nginx).

    Yields a dict of base URLs. Tears the stack down on teardown.
    """
    # Use a test compose override so the upstream is the mock (python)
    # instead of the real ollama image.
    override = REPO_ROOT / "tests" / "mock_upstream" / "docker-compose.override.yml"
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.yml",
            "-f",
            str(override),
            "up",
            "-d",
            "--build",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        check=True,
    )
    # Wait for nginx to be up
    _wait_http("http://127.0.0.1:8080/healthz", timeout=60)
    urls = {
        "nginx": "http://127.0.0.1:8080",
        "sidecar": "http://127.0.0.1:9090",
        "upstream": "http://127.0.0.1:11434",
    }
    try:
        yield urls
    finally:
        try:
            subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    "docker-compose.yml",
                    "-f",
                    str(override),
                    "down",
                    "-v",
                    "--remove-orphans",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# HTTP helpers (requests-based, shared across tests)
# ---------------------------------------------------------------------------


@pytest.fixture
def http():
    import requests

    s = requests.Session()
    yield s
