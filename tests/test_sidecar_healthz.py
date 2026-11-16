"""Sidecar /api/healthz — unit tests (hits sidecar directly)."""

from __future__ import annotations

import requests


def test_healthz_ok(sidecar: str) -> None:
    r = requests.get(f"{sidecar}/api/healthz", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


def test_healthz_is_json(sidecar: str) -> None:
    r = requests.get(f"{sidecar}/api/healthz", timeout=5)
    assert r.headers["Content-Type"].startswith("application/json")
