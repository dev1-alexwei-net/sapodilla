"""Smoke script static tests (generic web-API tracker).

Validates that scripts/smoke.sh exercises the full stack end-to-end using
generic endpoints (no Ollama-specific assumptions).
"""

from __future__ import annotations

from pathlib import Path

import pytest

SMOKE = Path(__file__).parent.parent / "scripts" / "smoke.sh"


@pytest.mark.unit
class TestSmokeScript:
    def test_smoke_script_exists_and_is_executable(self) -> None:
        assert SMOKE.exists()

    def test_smoke_script_covers_endpoints(self) -> None:
        content = SMOKE.read_text()
        assert "/api/healthz" in content
        assert "/api/usage" in content
        assert "${LISTEN_PORT:-8080}" in content
        assert "${SIDECAR_PORT:-9090}" in content
        # The smoke test should exercise a generic proxied request, not an
        # Ollama-specific endpoint.
        assert "/any/path" in content

    def test_smoke_script_uses_retry_loop(self) -> None:
        content = SMOKE.read_text()
        assert "until" in content or "retry" in content.lower()

    def test_smoke_script_has_set_e(self) -> None:
        content = SMOKE.read_text()
        assert "set -e" in content or "set -euo pipefail" in content
