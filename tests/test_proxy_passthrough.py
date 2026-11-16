"""Generic ping and echo responses pass through the proxy unchanged.

The NGINX front door forwards requests to the mock upstream and returns its
response to the caller.
"""

from __future__ import annotations

import requests


def test_proxy_passes_ping(proxy: str) -> None:
    r = requests.get(f"{proxy}/api/ping", timeout=10)
    assert r.status_code == 200
    assert r.headers["Content-Type"].startswith("application/json")
    data = r.json()
    assert data["upstream"] == "generic-mock"
    assert data["method"] == "GET"
    assert data["path"] == "/api/ping"


def test_proxy_passes_echo(proxy: str) -> None:
    """POST /echo returns the request body + metadata as JSON."""
    payload = {"hello": "world", "n": 42}
    r = requests.post(f"{proxy}/echo", json=payload, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data["method"] == "POST"
    assert data["path"] == "/echo"
    assert data["body"] == payload
