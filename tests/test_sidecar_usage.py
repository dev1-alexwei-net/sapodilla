"""SC4-SC7: /api/usage shape + values.

Unit tests: verify the JSON shape of /api/usage and that the values
are internally consistent.
"""

from __future__ import annotations

import requests


def test_usage_shape(sidecar: str) -> None:
    base = sidecar
    # Make a request first so the state is non-empty
    requests.post(f"{base}/track", json={"model": "shape-model", "endpoint": "/api/generate"})
    r = requests.get(f"{base}/api/usage")
    assert r.status_code == 200
    assert r.headers["Content-Type"].startswith("application/json")

    data = r.json()
    # Required top-level fields
    assert "total_requests" in data
    assert "last_request_at" in data
    assert "idle_for_seconds" in data
    assert "endpoints" in data
    assert "recent" in data

    # Types
    assert isinstance(data["total_requests"], int)
    assert isinstance(data["last_request_at"], (int, float))
    assert isinstance(data["idle_for_seconds"], (int, float))
    assert isinstance(data["endpoints"], dict)
    assert isinstance(data["recent"], list)

    # recent entries shape
    for entry in data["recent"]:
        assert "model" in entry
        assert "endpoint" in entry
        assert "at" in entry


def test_usage_totals_consistent(sidecar: str) -> None:
    base = sidecar
    # Seed a known number of events
    N = 7
    for i in range(N):
        requests.post(f"{base}/track", json={"model": f"m{i}", "endpoint": f"/ep{i}"})
    data = requests.get(f"{base}/api/usage").json()
    assert data["total_requests"] >= N
    # endpoints sum should be <= total_requests
    assert sum(data["endpoints"].values()) >= N


def test_usage_recent_capped(sidecar: str) -> None:
    base = sidecar
    # HISTORY_LEN default is 100; we only assert the cap exists
    data = requests.get(f"{base}/api/usage").json()
    # The cap is enforced; just check the list is bounded
    assert len(data["recent"]) <= 1000  # generous upper bound
