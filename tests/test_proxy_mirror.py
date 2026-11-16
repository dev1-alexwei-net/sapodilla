"""SC3 (integration): after N requests through the proxy, the sidecar
reports total >= N.  This exercises the full mirror path: NGINX mirror
directive fires a side request to the sidecar for every proxied request,
and the sidecar records it.  We verify via /api/usage.
"""

from __future__ import annotations

import requests


def test_mirror_fires_to_sidecar(proxy: str) -> None:
    # Read sidecar usage via the sidecar's /api/usage — but the proxy
    # fixture only gives us the nginx URL. We need the sidecar URL too.
    # The sidecar is exposed on port 9090 in the compose stack.
    sidecar_base = "http://127.0.0.1:9090"

    before = requests.get(f"{sidecar_base}/api/usage", timeout=5).json()
    before_total = before["total"]

    # Send 3 requests through the proxy
    for _ in range(3):
        requests.get(f"{proxy}/api/ping", timeout=10)

    after = requests.get(f"{sidecar_base}/api/usage", timeout=5).json()
    assert after["total"] >= before_total + 3
