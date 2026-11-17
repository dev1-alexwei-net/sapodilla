# Generic web-API usage sidecar

A small Go REST API that counts proxied requests. It is the core microservice
in this project: a lightweight, stateless usage tracker that records a request
total and the time of the latest request. It does not inspect request bodies or
payloads — it only counts.

Sapodilla exists so that your proxy server, like nginx, can mirror requests
to the tracking endpoint, e.g.:

```nginx
        mirror /track-usage-api;
```

The repository also includes an optional NGINX configuration and Compose stack
for local development and testing of that setup. In production you would
typically point your own proxy (or the API itself) at the endpoint.

## What the sidecar does

- Exposes a tiny REST API (`/track`, `/api/usage`, `/api/healthz`).
- Keeps a request counter in memory plus the timestamp of the most recent
  request.
- Is deliberately stateless about request content — it never reads or logs
  bodies, headers, or paths beyond an access log.
- Is cheap to run as a standalone container or sidecar alongside any API.

## Repository layout

```text
ollama-mirror/
├── go.mod                  # module root for the Go project and tests
├── src/                    # Go source files (usage-api binary)
└── test/                   # black-box Go API tests
compose.yaml
Dockerfile.usage-api        # the usage-api Go sidecar (the core component)
Dockerfile.mirror           # optional NGINX front-end for local dev
Dockerfile.echo-api
conftest.py
test_proxy.py              # pytest/Compose integration harness
nginx/                     # NGINX configuration (development-only mirror)
upstream/                  # local echo API implementation
```

## Quick start with Docker Compose

The Compose stack runs the usage-api sidecar together with the optional NGINX
mirror and a generic `echo-api` mock for trying the setup without another
service. Start the stack and send a request through the proxy:

```sh
docker compose up --build -d
curl -X POST http://localhost:8080/any/path -d '{"hello":"world"}'
curl http://localhost:9090/api/usage
```

To use another service reachable from the Compose network, set its host and
port before starting the stack. No image rebuild or file edit is needed:

```sh
LISTEN_PORT=9000 UPSTREAM_HOST=my-api UPSTREAM_PORT=3000 docker compose up -d
curl http://localhost:9000/any/path
```

If you only need the sidecar itself, run the usage-api container directly (see
below) and point your own proxy or client at it.

## Compose services

- `usage-api` — the Go REST API sidecar (the core component); published on
  loopback only.
- `mirror` — optional NGINX reverse proxy for local development, published on
  `LISTEN_HOST:LISTEN_PORT`.
- `echo-api` — local generic echo service for development and tests.

## Run the usage-api sidecar directly

The sidecar is the core of the project and can run as a standalone container.
It listens on `ADDR` (default `:9090`):

```sh
docker build -t usage-api:local -f Dockerfile.usage-api .
docker run -d --name usage-api -p 127.0.0.1:9090:9090 usage-api:local
```

For flag-based control when running the binary directly, precedence is
**`-addr` flag > `ADDR` environment variable > `:9090` default**.

### Optional: run the NGINX development mirror

If you want the bundled NGINX mirror in front of the sidecar (local dev/test),
put both on the same Docker network and point NGINX at your upstream. Replace
`my-api:3000` with a reachable service name and port:

```sh
docker network create usage-mirror
docker build -t usage-api:local -f Dockerfile.usage-api .
docker build -t web-api-mirror:local -f Dockerfile.mirror .

docker run -d --name usage-api --network usage-mirror \
  -p 127.0.0.1:9090:9090 -e ADDR=:9090 usage-api:local

docker run -d --name mirror --network usage-mirror -p 0.0.0.0:9000:9000 \
  -e LISTEN_PORT=9000 \
  -e UPSTREAM_HOST=my-api -e UPSTREAM_PORT=3000 \
  -e USAGE_API_HOST=usage-api -e USAGE_API_PORT=9090 web-api-mirror:local
```

The usage-api container must share a Docker network with the NGINX mirror.

## Configuration

Compose passes these variables into the containers. Unset or empty values use
the defaults below.

| Variable | Meaning | Default |
| --- | --- | --- |
| `ADDR` | usage-api listen address; Compose derives it from `USAGE_API_PORT` unless set | `:9090` |
| `LISTEN_HOST` | Host address used to publish the proxy port | `0.0.0.0` |
| `LISTEN_PORT` | Proxy port (container and published host port) | `8080` |
| `UPSTREAM_HOST` | API hostname as resolved by NGINX | `echo-api` |
| `UPSTREAM_PORT` | API port; also configures the bundled echo service | `11434` |
| `USAGE_API_HOST` | usage-api hostname as resolved by NGINX | `usage-api` |
| `USAGE_API_PORT` | usage-api port used by NGINX and Compose | `9090` |

The usage-api port is `USAGE_API_PORT`; `ADDR` sets the actual listen socket.
Keep them in sync when you override `ADDR` yourself.

## Usage API

- `GET /api/healthz` — liveness check.
- `POST /track` — metadata-only request target used by the NGINX mirror to
  record a request.
- `GET /api/usage` — returns `{ "total": number, "last_seen": epoch_milliseconds|null, "last_seen_datetime": rfc3339_datetime|null }`.

The counter is in memory and resets when the usage-api restarts. In the Compose
setup the usage-api is published on loopback only; the optional NGINX proxy is
published on `LISTEN_HOST`.

## Development

Run the Go API tests from its module root with `cd ollama-mirror && go test ./...`.
The Docker Compose integration suite runs from the repository root with
`python -m pytest -q`; it selects non-default ports to exercise the environment
variable configuration path.
