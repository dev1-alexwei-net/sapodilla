#!/usr/bin/env python3
"""Minimal Ollama mock for CI smoke tests.

Serves the few endpoints the sidecar/proxy need:
  GET  /api/tags   -> list of models
  POST /api/chat   -> canned response (counts as a "completion")
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODELS = ["llama3.2:1b", "llama3.2:3b"]


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/tags":
            self._send(200, {"models": [{"name": m, "size": 0} for m in MODELS]})
        elif self.path == "/api/version":
            self._send(200, {"version": "0.0.0-mock"})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        _body = self.rfile.read(length)
        if self.path == "/api/chat":
            self._send(
                200,
                {
                    "model": "llama3.2:1b",
                    "message": {"role": "assistant", "content": "hello from mock"},
                    "done": True,
                    "total_duration": 1,
                },
            )
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        print("[mock-ollama]", fmt % args, flush=True)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 11434), Handler)
    print("[mock-ollama] listening on 0.0.0.0:11434", flush=True)
    server.serve_forever()
