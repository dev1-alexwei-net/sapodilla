"""SC9 (integration): when the sidecar is down, proxied requests still
succeed — the mirror directive is fire-and-forget and must not break
the main request.
"""

from __future__ import annotations

import requests


def test_proxy_still_works_without_sidecar(proxy: str) -> None:
    """The proxy front door serves upstream traffic even when the
    sidecar is unreachable (the mirror side request fails silently)."""
    r = requests.get(f"{proxy}/api/ping", timeout=10)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
