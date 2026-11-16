"""Proxied requests still succeed when the sidecar is unavailable."""

from __future__ import annotations

import requests


def test_proxy_still_works_without_sidecar(proxy: str, sidecar_stopped: None) -> None:
    """The proxy serves upstream traffic while the mirror target is stopped."""
    r = requests.get(f"{proxy}/api/ping", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data["upstream"] == "generic-mock"
    assert data["method"] == "GET"
    assert data["path"] == "/api/ping"
