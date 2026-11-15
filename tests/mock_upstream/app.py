"""Mock Ollama upstream for hermetic testing.

Implements the two endpoints the test suite exercises:
  - GET  /api/tags      -> static JSON
  - POST /api/generate  -> SSE stream (2 chunks + done marker)

Pure stdlib (http.server) so no extra deps. Runs on a configurable
port, defaults to 11434 (to match Ollama's real port in compose).
"""
from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class MockOllamaHandler(BaseHTTPRequestHandler):
    # Suppress default logging (test noise)
    def log_message(self, fmt: str, *args: object) -> None:  # noqa: N802
        pass

    # --- GET /api/tags ---------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/tags":
            payload = {
                "models": [
                    {"name": "llama3:70b", "size": 3944241908,
                     "modified_at": "2025-01-01T00:00:00Z"},
                    {"name": "mistral:7b", "size": 4112519553,
                     "modified_at": "2025-01-01T00:00:00Z"},
                ]
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/api/version":
            payload = {"version": "0.9.9-mock"}
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_error(404, "not found")

    # --- POST /api/generate ----------------------------------------------
    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/generate":
            self.send_error(404, "not found")
            return

        # Read (and discard) the request body
        length = int(self.headers.get("Content-Length", 0))
        _ = self.rfile.read(length) if length else b""

        # Parse the model name so we can echo it back (tests may assert)
        model = "llama3:70b"
        if length:
            try:
                raw = self.rfile.read(0)  # already consumed; ignore
            except Exception:
                pass

        # Respond with SSE
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def sse(payload: dict) -> bytes:
            return f"data: {json.dumps(payload)}\n\n".encode("utf-8")

        # Chunk 1
        self.wfile.write(sse({
            "model": model,
            "created_at": "2025-01-01T00:00:00Z",
            "response": "Hello",
            "done": False,
        }))
        self.wfile.flush()
        time.sleep(0.05)
        # Chunk 2
        self.wfile.write(sse({
            "model": model,
            "created_at": "2025-01-01T00:00:00Z",
            "response": " world",
            "done": False,
        }))
        self.wfile.flush()
        time.sleep(0.05)
        # Done marker
        self.wfile.write(sse({
            "model": model,
            "created_at": "2025-01-01T00:00:00Z",
            "response": "",
            "done": True,
            "total_duration": 100_000_000,
            "load_duration": 1_000_000,
            "prompt_eval_count": 10,
            "eval_count": 5,
        }))
        self.wfile.flush()


def serve(port: int) -> None:
    httpd = ThreadingHTTPServer(("0.0.0.0", port), MockOllamaHandler)
    print(f"mock-ollama listening on :{port}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=11434)
    args = parser.parse_args()
    serve(args.port)


if __name__ == "__main__":
    main()
