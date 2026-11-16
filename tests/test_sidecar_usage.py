"""/api/usage — unit tests (hits sidecar directly).

The sidecar returns a minimal JSON object with only two fields:
  total      int    cumulative request count
  last_seen  string ISO-8601 UTC timestamp (or null if no requests yet)
"""

from __future__ import annotations

import requests


def test_usage_shape(sidecar: str) -> None:
    # Make a request first so the state is non-empty
    requests.post(f"{sidecar}/track", timeout=5)
    r = requests.get(f"{sidecar}/api/usage", timeout=5)
    assert r.status_code == 200
    assert r.headers["Content-Type"].startswith("application/json")

    data = r.json()
    assert "total" in data
    assert "last_seen" in data
    assert isinstance(data["total"], int)
    assert data["total"] >= 1
    assert isinstance(data["last_seen"], str)
    # No legacy fields
    assert "models" not in data
    assert "endpoints" not in data
    assert "recent" not in data


def test_usage_total_increments(sidecar: str) -> None:
    before = requests.get(f"{sidecar}/api/usage", timeout=5).json()["total"]
    for _ in range(3):
        requests.post(f"{sidecar}/track", timeout=5)
    after = requests.get(f"{sidecar}/api/usage", timeout=5).json()["total"]
    assert after == before + 3


def test_usage_last_seen_advances(sidecar: str) -> None:
    t0 = requests.get(f"{sidecar}/api/usage", timeout=5).json()
    requests.post(f"{sidecar}/track", timeout=5)
    t1 = requests.get(f"{sidecar}/api/usage", timeout=5).json()
    if t0["last_seen"] is not None:
        assert t1["last_seen"] >= t0["last_seen"]
