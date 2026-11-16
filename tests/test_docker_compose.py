"""Docker Compose configuration tests (generic web-API tracker)."""

from __future__ import annotations

import pytest


@pytest.mark.docker
class TestDockerCompose:
    def test_docker_compose_declares_all_services(self, compose: str) -> None:
        assert "nginx" in compose
        assert "sidecar" in compose
        assert "upstream" in compose

    def test_docker_compose_ports_are_configurable(self, compose: str) -> None:
        assert "${LISTEN_PORT:-8080}" in compose
        assert "${SIDECAR_PORT:-9090}" in compose
        assert "${UPSTREAM_PORT:-11434}" in compose

    def test_docker_compose_hosts_are_configurable(self, compose: str) -> None:
        for name in ("LISTEN_HOST", "UPSTREAM_HOST", "SIDECAR_HOST"):
            assert name in compose

    def test_docker_compose_sidecar_port_is_loopback_only(self, compose: str) -> None:
        # The sidecar API is available on localhost, not on all host interfaces.
        assert '"127.0.0.1:${SIDECAR_PORT:-9090}:${SIDECAR_PORT:-9090}"' in compose

    def test_docker_compose_does_not_configure_unused_persistence(self, compose: str) -> None:
        """The counter is in memory and resets when the sidecar restarts."""
        assert "STATE_DIR" not in compose
        assert "sidecar-data" not in compose

    def test_docker_compose_uses_network(self, compose: str) -> None:
        assert "mirror" in compose
        assert "networks:" in compose
