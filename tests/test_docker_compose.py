"""Docker Compose configuration tests (generic web-API tracker)."""

from __future__ import annotations

import pytest


@pytest.mark.docker
class TestDockerCompose:
    def test_docker_compose_declares_all_services(self, compose: str) -> None:
        assert "nginx" in compose
        assert "sidecar" in compose
        assert "upstream" in compose

    def test_docker_compose_ports(self, compose: str) -> None:
        # nginx listens on 8080; upstream (generic mock) on 11434.
        assert "8080:8080" in compose
        assert "11434" in compose

    def test_docker_compose_upstream_var(self, compose: str) -> None:
        """The upstream is configurable via the UPSTREAM env var."""
        assert "UPSTREAM" in compose

    def test_docker_compose_sidecar_exposes_no_public_port(self, compose: str) -> None:
        # The sidecar should not be exposed publicly; only reachable on the
        # internal mirror network.
        sidecar_section = compose.split("sidecar:", 1)[1].split("upstream:", 1)[0]
        assert "ports:" not in sidecar_section

    def test_docker_compose_sidecar_data_persists(self, compose: str) -> None:
        """The sidecar's counter state survives restarts via a named volume."""
        assert "sidecar-data" in compose
        assert "volumes:" in compose

    def test_docker_compose_uses_network(self, compose: str) -> None:
        assert "mirror" in compose
        assert "networks:" in compose
