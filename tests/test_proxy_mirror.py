"""Requests proxied through NGINX are counted by the sidecar.

This exercises the mirror path: NGINX sends a metadata-only subrequest to the
sidecar for each proxied request, and the sidecar records the count.
"""

from __future__ import annotations

import requests


def test_mirror_fires_to_sidecar(proxy: str, compose_sidecar: str) -> None:
    before = requests.get(f"{compose_sidecar}/api/usage", timeout=5).json()
    before_total = before["total"]

    # Send 3 requests through the proxy
    for _ in range(3):
        requests.get(f"{proxy}/api/ping", timeout=10)

    after = requests.get(f"{compose_sidecar}/api/usage", timeout=5).json()
    assert after["total"] >= before_total + 3
