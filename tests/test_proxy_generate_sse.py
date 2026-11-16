"""SC8: upstream /echo returns the request body as JSON (integration).

Replaces the old SSE streaming test — the generic upstream has no
streaming endpoint.  The key assertion is that the proxy correctly
forwards and returns the upstream's JSON response.
"""

from __future__ import annotations

import requests


def test_proxy_echo_returns_json(proxy: str) -> None:
    payload = {"msg": "hello", "count": 7}
    r = requests.post(f"{proxy}/echo", json=payload, timeout=10)
    assert r.status_code == 200
    assert r.headers["Content-Type"].startswith("application/json")
    data = r.json()
    assert data["body"] == payload
    assert data["method"] == "POST"
    assert data["path"] == "/echo"


def test_proxy_get_ping(proxy: str) -> None:
    r = requests.get(f"{proxy}/api/ping", timeout=10)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
