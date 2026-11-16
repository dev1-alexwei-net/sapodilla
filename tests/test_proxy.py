"""End-to-end proxy and sidecar integration checks."""

from __future__ import annotations

from pathlib import Path

import requests


class TestProxy:
    def test_ping_passthrough(self, proxy: str) -> None:
        response = requests.get(f"{proxy}/api/ping", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data["upstream"] == "generic-mock"
        assert data["method"] == "GET"
        assert data["path"] == "/api/ping"
        assert data["body_bytes"] == 0

    def test_echo_passthrough(self, proxy: str) -> None:
        payload = {"hello": "world", "n": 42}
        response = requests.post(f"{proxy}/echo", json=payload, timeout=10)
        assert response.status_code == 200
        assert response.json()["body"] == payload
        assert response.json()["path"] == "/echo"

    def test_mirrors_requests(self, proxy: str, compose_sidecar: str) -> None:
        before = requests.get(f"{compose_sidecar}/api/usage", timeout=5).json()["total"]
        for _ in range(3):
            requests.get(f"{proxy}/api/ping", timeout=10)
        after = requests.get(f"{compose_sidecar}/api/usage", timeout=5).json()["total"]
        assert after >= before + 3

    def test_passes_through_when_sidecar_is_down(self, proxy: str, sidecar_stopped: None) -> None:
        response = requests.get(f"{proxy}/api/ping", timeout=10)
        assert response.status_code == 200
        assert response.json()["upstream"] == "generic-mock"

    def test_sidecar_port_is_loopback_only(self) -> None:
        compose = (Path(__file__).parents[1] / "docker-compose.yml").read_text()
        assert '"127.0.0.1:${SIDECAR_PORT:-9090}:${SIDECAR_PORT:-9090}"' in compose
