# Architecture

## Goal

A lightweight pass-through proxy that tracks **service usage metadata** (who hit what, when) so we can answer: **"has this service had no users recently?"**

The proxy is not the source of truth for the application. It sits in front, forwards everything, and quietly records a lightweight trail of requests. Usage is exposed via a small REST API on the same front-door port.

## Design decisions

| Decision | Choice | Why |
|---|---|---|
| Pass-through | **NGINX** | Mature, lightweight, no application code in the data path. `mirror` directive fires a copy of each request to a sidecar for tracking. |
| Tracker backend | **Go** | Single static binary, tiny image, fast. In-memory state only (no DB) — this is a metadata signal, not a system of record. |
| Trigger | **On request** (not on response completion) | "When has the service had no users?" is answered by request count + last-seen timestamp. Response bytes/duration would require the Go service to be the pass-through itself (heavier, out of scope). |
| State | **In-memory ring buffer** | Restart resets counters. Acceptable for a "has anyone been using this?" signal. |
| Test stack | **uv + pyproject + pytest** | Fast, pinned, portable. Tests are the first-class artifact (TDD). |

## Components

### 1. NGINX proxy (the "proxy" image)

- Listens on `:8080` (configurable via `LISTEN_PORT`).
- `location /` → `proxy_pass http://upstream;` where `upstream` is the target service (Ollama on `:11434`, or any other service).
- `mirror http://sidecar:9090/track;` — fires a **metadata-only copy** of each request to the Go sidecar. No request body (`mirror_request_body off`), no response copy. This is the usage signal.
- `location = /api/usage` → `proxy_pass http://sidecar:9090/api/usage;` — read-only passthrough to the sidecar's usage API.
- `location = /api/healthz` → `proxy_pass http://sidecar:9090/api/healthz;` — composite health (proxy ok + upstream reachable).
- Streaming-friendly: `proxy_buffering off`, `proxy_read_timeout 300s`, `proxy_http_version 1.1`, `proxy_set_header Connection ""`.
- **Ollama-safe**: SSE (`/api/generate`, `/api/chat`) works because buffering is off and we never touch the body.

### 2. Go sidecar (usage tracker)

Single binary, no external deps (stdlib only). Ports: `:9090` (internal).

**State** (in-memory, mutex-guarded):
- `total_requests int64` — cumulative count.
- `last_request_at *time.Time` — when the most recent request was seen.
- `endpoints map[string]int64` — per-URI counts.
- `recent []Entry` — ring buffer of the last `HISTORY_LEN` (default 200) entries: `{ts, method, uri, client_ip}`.

**Endpoints**:
- `POST /track` — receives mirrored requests. Updates state. Returns `204 No Content`. (Called by NGINX `mirror`, never by clients.)
- `GET /api/usage` — returns:
  ```json
  {
    "total_requests": 1234,
    "last_request_at": "2026-11-15T18:00:00Z",
    "idle_for_seconds": 742,
    "endpoints": { "/api/tags": 500, "/api/generate": 734 },
    "recent": [ { "ts": "...", "method": "GET", "uri": "/api/tags", "client_ip": "10.0.0.5" } ]
  }
  ```
  `idle_for_seconds` is the key "no users" signal: seconds since the last request.
- `GET /api/healthz` — returns `{ "proxy": "ok", "upstream": "online|offline" }`. Pokes `UPSTREAM_HEALTH_URL` (default `http://upstream:11434/api/tags`) with a short timeout.

**Config via env**: `PORT` (default `9090`), `HISTORY_LEN` (default `200`), `UPSTREAM_HEALTH_URL` (default `http://127.0.0.1:11434/api/tags`), `UPSTREAM_HEALTH_TIMEOUT_MS` (default `2000`).

### 3. Docker Compose (test scaffolding)

Three services:
- `upstream` — the service being tracked. For testing, a small **mock upstream** (Python/uv) that mimics Ollama's shape: `GET /api/tags` returns a fixed JSON, `POST /api/generate` returns an SSE stream. This keeps tests hermetic (no real Ollama needed). A second compose profile (`ollama`) can swap in a real Ollama image.
- `sidecar` — Go binary, built from `Dockerfile.sidecar`. Internal port `9090`. Depends on nothing (stateless w.r.t. upstream).
- `proxy` — NGINX, built from `Dockerfile.proxy` (base `nginx:1.27-alpine` + our conf). Exposes `8080`. Depends on `upstream` + `sidecar`.

`docker compose up` → clients talk to `:8080` → NGINX mirrors to sidecar → NGINX forwards to upstream. Single front door.

## Data flow (per request)

```
client ──► NGINX :8080
            ├──► (main)  upstream :11434   ──► response streams back to client
            └──► (mirror) sidecar :9090/track  ──► updates in-memory state ──► 204
```

The mirror subrequest is fired **when the main request is sent** (not when it completes). For SSE responses this is fine: the counter increments at request start, which is exactly when a "user touched the service" event happens.

## What we are NOT doing (scope boundary)

- **No response bytes or duration.** Would require the Go service to be the pass-through.
- **No persistence.** In-memory only. Restart = counter reset.
- **No authentication** on the sidecar. Internal port, compose-network only.
- **No per-user identity** beyond client IP. Ollama is single-tenant local.

## Threat / edge cases

- **Sidecar down** → NGINX `mirror` failures are logged but do NOT block the main request. Pass-through still works. (Document + test.)
- **Upstream down** → NGINX returns 502. Sidecar `last_request_at` still updates (a request was made). Healthz reports `upstream: offline`.
- **SSE long streams** → `proxy_buffering off` + no body touch means no buffering pressure. Mirror fires at start, not at end.
