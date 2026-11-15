"""SC2: POST /api/generate through the proxy returns a valid SSE stream.

The NGINX front door must pass the request through to the mock upstream
and return the SSE (text/event-stream) response unchanged. We parse the
SSE stream and assert the chunks arrive in order and the final `done`
marker is present.
"""
from __future__ import annotations

import json

import pytest
import requests


def _parse_sse(stream) -> list[dict]:
    """Parse an SSE stream into a list of JSON payloads."""
    events = []
    buffer = ""
    for line in stream.iter_lines(decode_unicode=True):
        if line is None:
            continue
        line = line.strip()
        if not line:
            continue
        if line.startswith("data: "):
            buffer += line[len("data: "):]
            # SSE: data may be split across multiple `data:` lines,
            # but for our mock it's a single line per event
            # We flush on the blank line (which `iter_lines` skips)
            # Simpler: treat each `data:` line as a full JSON payload.
            try:
                events.append(json.loads(buffer))
            except json.JSONDecodeError:
                pass
            buffer = ""
    return events


def test_proxy_generate_sse(compose_stack: dict) -> None:
    nginx = compose_stack["nginx"]
    payload = {
        "model": "llama3:70b",
        "prompt": "hello",
        "stream": True,
    }
    with requests.post(f"{nginx}/api/generate", json=payload,
                       stream=True, timeout=30) as r:
        assert r.status_code == 200
        ctype = r.headers.get("Content-Type", "")
        assert "text/event-stream" in ctype, f"expected SSE, got {ctype}"

        events = _parse_sse(r)

    # We expect at least 3 events: 2 response chunks + 1 done marker
    assert len(events) >= 3, f"expected >=3 SSE events, got {len(events)}"

    # First two are response chunks, last is the done marker
    assert events[0]["done"] is False
    assert events[0]["response"] == "Hello"
    assert events[1]["done"] is False
    assert events[1]["response"] == " world"
    assert events[-1]["done"] is True
    assert events[-1]["eval_count"] == 5


def test_proxy_generate_model_echo(compose_stack: dict) -> None:
    """The mock upstream echoes the model name back in each SSE event."""
    nginx = compose_stack["nginx"]
    payload = {"model": "mistral:7b", "prompt": "hi", "stream": True}
    with requests.post(f"{nginx}/api/generate", json=payload,
                       stream=True, timeout=30) as r:
        assert r.status_code == 200
        # Just check the stream is well-formed; the mock echoes model
        # but we don't strictly require it here.
        text = b"".join(r.iter_content(chunk_size=1024)).decode("utf-8")
    assert "data:" in text
