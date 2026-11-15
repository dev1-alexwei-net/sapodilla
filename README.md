# ollama-mirror — sidecar

Usage-tracking sidecar. See ARCHITECTURE.md.

## Run locally

```bash
go run .
```

Listens on `:9090`.

## Endpoints

- `GET /api/healthz` — liveness probe.
- `POST /track` — fired by NGINX mirror (ticket 2).
- `GET /api/usage` — usage snapshot (ticket 3).
