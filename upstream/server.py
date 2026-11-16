"""Generic mock upstream for the web-API usage tracker.

This is NOT an Ollama server. It is a stand-in for *any* web API the mirror
is configured to proxy to. For testing, it behaves generically:

- ``GET /healthz`` -> ``200 ok`` (used for readiness / healthchecks).
- any request carrying ``?stream=1`` -> a chunked streaming body (used to
  verify the proxy does not buffer).
- any other request -> a JSON echo describing the request it received
  (method, path, query, selected headers, body). This lets the test-suite
  assert that the proxy forwarded the request faithfully, regardless of the
  endpoint the client targeted.

The real deployment points the mirror at a real API (Ollama, a custom
service, any HTTP endpoint). This server only exists to exercise the
proxy + sidecar in CI and local smoke tests.

Run locally:
    python3 server.py 9090   # or any port; default 11434 for compatibility
"""

from __future__ import annotations

import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _stream_body() -> bytes:
    # Two chunks with a delay, mimicking an LLM token stream.
    return b"chunk-1\n\0chunk-2\n"


class UpstreamHandler(BaseHTTPRequestHandler):
    """Echo any request back as JSON; stream when ?stream=1 is present."""

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length > 0 else b""

    def _respond(
        self,
        status: int,
        body: bytes,
        content_type: str = "application/json",
        extra: dict | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _echo(self) -> None:
        raw = self._read_body()
        payload = {
            "upstream": "generic-mock",
            "method": self.command,
            "path": self.path,
            "received_at": time.time(),
            "body_bytes": len(raw),
        }
        if raw:
            try:
                payload["body"] = json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                payload["body"] = raw.decode("utf-8", errors="replace")
        self._respond(200, json.dumps(payload).encode("utf-8"))

    def _stream(self) -> None:
        self._read_body()  # drain request body first
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        for chunk in (b"chunk-1\n", b"chunk-2\n", b""):
            self.wfile.write(chunk)
            self.wfile.flush()
            time.sleep(0.02)

    def _route(self) -> None:
        if self.path == "/healthz":
            self._read_body()
            self._respond(200, b"ok", content_type="text/plain")
            return
        # Treat any path with a stream query param (or 'stream' segment) as streaming.
        if "stream=1" in self.path or "/stream" in self.path:
            self._stream()
            return
        self._echo()

    # HTTP verbs all funnel through the same generic routing.
    do_GET = _route  # noqa: N815
    do_POST = _route  # noqa: N815
    do_PUT = _route  # noqa: N815
    do_DELETE = _route  # noqa: N815
    do_PATCH = _route  # noqa: N815
    do_HEAD = _route  # noqa: N815

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: N802
        sys.stderr.write("[upstream] %s\n" % (fmt % args))


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 11434
    ThreadingHTTPServer(("0.0.0.0", port), UpstreamHandler).serve_forever()


if __name__ == "__main__":
    main()
