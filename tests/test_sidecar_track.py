"""Sidecar /track endpoint — unit tests (hits sidecar directly).

The sidecar records a count for any request to /track regardless of
method, path, or body content.
"""

from __future__ import annotations

import requests


def test_track_increments_total(sidecar: str) -> None:
    before = requests.get(f"{sidecar}/api/usage", timeout=5).json()
    before_total = before["total"]

    r = requests.post(f"{sidecar}/track", timeout=5)
    assert r.status_code == 200

    after = requests.get(f"{sidecar}/api/usage", timeout=5).json()
    assert after["total"] == before_total + 1


def test_track_any_method_counts(sidecar: str) -> None:
    before = requests.get(f"{sidecar}/api/usage", timeout=5).json()["total"]

    # GET, PUT, DELETE — all should increment
    requests.get(f"{sidecar}/track", timeout=5)
    requests.put(f"{sidecar}/track", data="x", timeout=5)
    requests.delete(f"{sidecar}/track", timeout=5)

    after = requests.get(f"{sidecar}/api/usage", timeout=5).json()["total"]
    assert after == before + 3


def test_track_empty_body_ok(sidecar: str) -> None:
    before = requests.get(f"{sidecar}/api/usage", timeout=5).json()["total"]
    r = requests.post(f"{sidecar}/track", timeout=5)
    assert r.status_code == 200
    after = requests.get(f"{sidecar}/api/usage", timeout=5).json()["total"]
    assert after == before + 1


def test_track_multiple_requests_accumulate(sidecar: str) -> None:
    before = requests.get(f"{sidecar}/api/usage", timeout=5).json()["total"]
    for _ in range(5):
        requests.post(f"{sidecar}/track", timeout=5)
    after = requests.get(f"{sidecar}/api/usage", timeout=5).json()["total"]
    assert after == before + 5
