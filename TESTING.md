# Test Plan & Success Criteria

TDD-first. Tests are the first-class artifact; every ticket's acceptance criteria is expressed as a test that must pass.

## Test stack

- **uv** — pinned Python env (`pyproject.toml` + `uv.lock`).
- **pytest** — unit + integration tests.
- **Test layers**:
  1. **Unit (Python, against the Go sidecar over HTTP)** — sidecar is the only stateful component. We test it directly via `requests` against a running instance (pytest fixture starts the Go binary on a test port).
  2. **Integration (compose)** — `docker compose up` with the mock upstream, hit the NGINX front door, verify the mirror fired and the sidecar state is correct. Uses `docker` + `requests` from the test suite.
  3. **Smoke (shell)** — `scripts/smoke.sh` runs the full cycle headlessly (used in CI too).

## Test principles

- **Hermetic.** No real Ollama. The mock upstream (Python) mimics Ollama's `/api/tags` + `/api/generate` (SSE) so tests are fast and deterministic.
- **Deterministic timing.** "Idle" assertions use a small clock tolerance (±5s) and a `time.sleep` long enough to be unambiguous.
- **No flakiness budget.** If a test flakes, fix the test before moving on. SSE timing is the most likely flake source; bound it.

## Success criteria (definition of done for the project)

| # | Criterion | Verified by |
|---|---|---|
| SC1 | `GET /api/tags` through the proxy returns the upstream's JSON unchanged (pass-through works). | integration |
| SC2 | `POST /api/generate` through the proxy returns a valid SSE stream (streaming works, no buffering corruption). | integration |
| SC3 | After N requests through the proxy, `GET /api/usage` reports `total_requests >= N`. | unit + integration |
| SC4 | `GET /api/usage.last_request_at` reflects the most recent request (within tolerance). | unit |
| SC5 | `GET /api/usage.idle_for_seconds` is small right after a request, and grows after quiescence. | unit |
| SC6 | `GET /api/usage.endpoints` correctly counts per-URI. | unit |
| SC7 | `GET /api/usage.recent` contains the last N entries in order, capped at `HISTORY_LEN`. | unit |
| SC8 | `GET /api/healthz` returns `upstream: "online"` when upstream is up, `"offline"` when down (kill upstream, re-query). | integration |
| SC9 | Sidecar down does NOT break pass-through (main request still succeeds, 502 if upstream also down). | integration |
| SC10 | `docker compose up` from a clean checkout works, `scripts/smoke.sh` exits 0. | smoke |
| SC11 | `uv run pytest -q` is green from a clean checkout. | unit+integration |
| SC12 | No secrets or real Ollama in the test path. | code review |

## Per-ticket test mapping

Each ticket below lists the tests that gate it. A ticket is not "done" until its tests are written (red) and passing (green).

## Test directory layout

```
tests/
  conftest.py          # fixtures: sidecar (Go binary) on a test port, mock upstream, compose stack
  test_sidecar_track.py       # SC3–SC7: /track increments state
  test_sidecar_usage.py       # SC4–SC7: /api/usage shape + values
  test_sidecar_healthz.py     # SC8: /api/healthz upstream online/offline
  test_proxy_passthrough.py   # SC1–SC2: NGINX forwards tags + SSE unchanged
  test_proxy_mirror.py        # SC3: mirror fires to sidecar (visible in /api/usage)
  test_sidecar_down.py        # SC9: pass-through survives sidecar outage
  test_smoke.py               # SC10–SC12: full compose cycle
  mock_upstream/
    app.py             # FastAPI/Flask mock: /api/tags, /api/generate (SSE)
```
