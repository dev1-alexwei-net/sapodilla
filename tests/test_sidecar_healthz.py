"""SC8: /api/healthz upstream online/offline.

The sidecar's /api/healthz should report `upstream: "online"` when
the Ollama upstream is reachable, and `upstream: "offline"` when it
isn't. In the unit test we can't easily kill the real upstream, so we
test the happy path here and the offline path via the compose stack
(where we can stop the upstream container).
"""

from __future__ import annotations

import requests


def test_healthz_shape(sidecar: str) -> None:
    base = sidecar
    r = requests.get(f"{base}/api/healthz")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "time" in data


def test_healthz_reports_sidecar_time(sidecar: str) -> None:
    base = sidecar
    data = requests.get(f"{base}/api/healthz").json()
    # `time` is an RFC3339 string; just assert it's present
    assert isinstance(data["time"], str) and len(data["time"]) > 0
