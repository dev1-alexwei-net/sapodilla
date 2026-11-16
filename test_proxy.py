from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from conftest import Session


class TestProxy:
    def test_passthrough(self, session: Session) -> None:
        get = session["client"].get(f"{session['proxy']}/api/ping", timeout=10)
        post = session["client"].post(
            f"{session['proxy']}/echo", json={"hello": "world", "n": 42}, timeout=10
        )
        assert get.status_code == post.status_code == 200
        assert (get.json()["method"], get.json()["path"]) == ("GET", "/api/ping")
        assert post.json()["body"] == {"hello": "world", "n": 42}

    def test_mirrors_requests(self, session: Session, usage_before: int) -> None:
        for _ in range(3):
            session["client"].get(f"{session['proxy']}/api/ping", timeout=10)
        assert (
            session["client"].get(f"{session['usage_api']}/api/usage", timeout=5).json()["total"]
            >= usage_before + 3
        )

    def test_usage_api_port_is_loopback_only(self, session: Session) -> None:
        assert '"127.0.0.1:${USAGE_API_PORT:-9090}:${USAGE_API_PORT:-9090}"' in session["compose"]
