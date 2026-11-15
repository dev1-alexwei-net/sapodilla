"""SC3 (integration): after N requests through the proxy, the sidecar
reports total_requests >= N.

This exercises the full mirror path: NGINX mirror directive fires a
side request to the sidecar for every proxied Ollama request, and the
sidecar records it. We verify via /api/usage.
"""
from __future__ import annotations

import pytest
import requests


def test_mirror_fires_to_sidecar(compose_stack: dict) -> None:
    nginx = compose_stack["nginx"]
    sidecar = compose_stack["sidecar"]

    # Baseline
    before = requests.get(f"{sidecar}/api/usage").json()
    before_total = before["total_requests"]

    # Fire 4 requests through the NGINX front door
    for i in range(4):
        r = requests.post(
            f"{nginx}/api/generate",
            json={"model": f"mirror-model-{i}", "prompt": f"p{i}",
                  "stream": False},
            timeout=15,
        )
        assert r.status_code == 200, f"request {i} failed: {r.status_code}"

    # Give the mirror subrequests a moment to land
    import time
    deadline = time.monotonic() + 10
    after = requests.get(f"{sidecar}/api/usage").json()
    while after["total_requests"] < before_total + 4 and time.monotonic() < deadline:
        time.sleep(0.25)
        after = requests.get(f"{sidecar}/api/usage").json()

    assert after["total_requests"] >= before_total + 4, (
        f"mirror did not fire: before={before_total}, after={after['total_requests']}"
    )


def test_mirror_records_model(compose_stack: dict) -> None:
    """The sidecar should have recorded at least one of the models we sent."""
    nginx = compose_stack["nginx"]
    sidecar = compose_stack["sidecar"]

    marker_model = "mirror-marker-model-xyz"
    requests.post(
        f"{nginx}/api/generate",
        json={"model": marker_model, "prompt": "x", "stream": False},
        timeout=15,
    )
    import time
    deadline = time.monotonic() + 10
    found = False
    while time.monotonic() < deadline and not found:
        data = requests.get(f"{sidecar}/api/usage").json()
        for entry in data["recent"]:
            if entry.get("model") == marker_model:
                found = True
                break
        if not found:
            time.sleep(0.25)

    assert found, f"model {marker_model} not recorded in sidecar recent list"
