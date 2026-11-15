"""SC3-SC7: /track increments sidecar state.

Unit tests: hit the sidecar's /track endpoint directly with various
payloads and assert that /api/usage reflects the change.
"""

from __future__ import annotations

import time

import requests

# ---------------------------------------------------------------------------
# SC3: total_requests increments per /track call
# ---------------------------------------------------------------------------


def test_track_increments_total(sidecar: str) -> None:
    base = sidecar
    before = requests.get(f"{base}/api/usage").json()
    before_total = before["total_requests"]

    # Fire 5 track events with different models
    for i in range(5):
        r = requests.post(
            f"{base}/track",
            json={"model": f"test-model-{i}", "endpoint": "/api/generate"},
        )
        assert r.status_code in (200, 204), r.text

    after = requests.get(f"{base}/api/usage").json()
    assert after["total_requests"] == before_total + 5


# ---------------------------------------------------------------------------
# SC6: endpoints count per URI
# ---------------------------------------------------------------------------


def test_track_counts_endpoints(sidecar: str) -> None:
    base = sidecar
    # 3 requests to /api/generate, 2 to /api/chat
    for _ in range(3):
        requests.post(f"{base}/track", json={"model": "m1", "endpoint": "/api/generate"})
    for _ in range(2):
        requests.post(f"{base}/track", json={"model": "m1", "endpoint": "/api/chat"})

    after = requests.get(f"{base}/api/usage").json()
    eps = after["endpoints"]
    assert eps.get("/api/generate", 0) >= 3
    assert eps.get("/api/chat", 0) >= 2


# ---------------------------------------------------------------------------
# SC4: last_request_at reflects most recent request (within tolerance)
# ---------------------------------------------------------------------------


def test_track_updates_last_request_at(sidecar: str) -> None:
    base = sidecar
    t0 = time.time()
    requests.post(f"{base}/track", json={"model": "m1", "endpoint": "/api/generate"})

    after = requests.get(f"{base}/api/usage").json()
    last = after["last_request_at"]
    # last_request_at is a unix timestamp
    assert last >= t0 - 1
    assert last <= time.time() + 1


# ---------------------------------------------------------------------------
# SC5: idle_for_seconds grows after quiescence
# ---------------------------------------------------------------------------


def test_track_idle_grows(sidecar: str) -> None:
    base = sidecar
    # Make a request
    requests.post(f"{base}/track", json={"model": "m1", "endpoint": "/api/generate"})
    after_immediate = requests.get(f"{base}/api/usage").json()
    idle_immediate = after_immediate["idle_for_seconds"]
    assert idle_immediate < 5, f"idle should be small right after request: {idle_immediate}"

    # Wait, then re-check
    time.sleep(3)
    after_wait = requests.get(f"{base}/api/usage").json()
    idle_after = after_wait["idle_for_seconds"]
    assert idle_after > idle_immediate, f"idle should grow: {idle_immediate} -> {idle_after}"


# ---------------------------------------------------------------------------
# SC7: recent list contains last N entries in order
# ---------------------------------------------------------------------------


def test_track_recent_order(sidecar: str) -> None:
    base = sidecar
    markers = ["A", "B", "C", "D"]
    for m in markers:
        requests.post(f"{base}/track", json={"model": f"model-{m}", "endpoint": "/api/generate"})

    after = requests.get(f"{base}/api/usage").json()
    recent = after["recent"]
    # The last 4 entries should be our markers in order
    tail = recent[-len(markers) :]
    assert [e["model"] for e in tail] == markers


# ---------------------------------------------------------------------------
# /track rejects bad input
# ---------------------------------------------------------------------------


def test_track_rejects_missing_model(sidecar: str) -> None:
    base = sidecar
    r = requests.post(f"{base}/track", json={"endpoint": "/api/generate"})
    # Should be 400 (or 422) — model is required
    assert r.status_code in (400, 422), f"expected 400/422, got {r.status_code}"


def test_track_rejects_malformed_json(sidecar: str) -> None:
    base = sidecar
    r = requests.post(
        f"{base}/track",
        data=b"not json at all",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code in (400, 422), f"expected 400/422, got {r.status_code}"
