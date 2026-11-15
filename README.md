# ollama-mirror

Lightweight usage-tracking proxy: **NGINX pass-through** + **Go sidecar** that exposes service usage metadata via REST. Built to answer one question — **"has this service had no users recently?"** — without adding weight to the data path.

- Pass-through: NGINX (streaming/SSE-safe, no request bodies touched)
- Tracker: Go, in-memory, stdlib-only
- Trigger: on request (mirror directive), not on response completion
- Tests first: uv + pyproject + pytest (TDD)
- Test scaffolding: docker compose with a hermetic mock upstream

See [ARCHITECTURE.md](./ARCHITECTURE.md) and [TESTING.md](./TESTING.md) for the design and the test plan.

## Quick start (once implemented)

```sh
uv sync
docker compose up --build
# clients → http://localhost:8080 (proxy)
curl http://localhost:8080/api/usage
```

## Status

Planning phase. See the open issues for the ticket series that takes this to completion.
