"""SC1: GET /api/tags through the proxy returns the upstream's JSON unchanged.

Integration test: requires the docker compose stack (mock upstream +
nginx + sidecar). The nginx front door (port 8080) must pass through
to the mock Ollama upstream (port 11434) and return the JSON body
unchanged.
"""

from __future__ import annotations

import requests


def test_proxy_passes_tags(compose_stack: dict) -> None:
    nginx = compose_stack["nginx"]
    r = requests.get(f"{nginx}/api/tags", timeout=10)
    assert r.status_code == 200
    assert r.headers["Content-Type"].startswith("application/json")
    data = r.json()
    assert "models" in data
    names = [m["name"] for m in data["models"]]
    # Mock upstream serves llama3:70b and mistral:7b
    assert "llama3:70b" in names
    assert "mistral:7b" in names


def test_proxy_passes_version(compose_stack: dict) -> None:
    nginx = compose_stack["nginx"]
    r = requests.get(f"{nginx}/api/version", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "version" in data
    assert "mock" in data["version"]
