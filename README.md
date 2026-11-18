# Generic web-API usage mirror

A small NGINX reverse proxy with a Go REST API that counts proxied requests. It
forwards any HTTP method, path, query, and body to your API; the usage API stores
only a total and the time of the latest request. It does not inspect requests.

## Repository layout

```text
sapodilla/
├── go.mod                  # module root for the Go project and tests
├── src/                    # two Go source files
└── test/                   # black-box Go API tests
compose.yaml
Dockerfile.mirror
Dockerfile.sapodilla
Dockerfile.echo-api
conftest.py
test_proxy.py              # pytest/Compose integration harness
nginx/                     # NGINX configuration
upstream/                  # local echo API implementation
```

## Quick start with Docker Compose

The included `echo-api` service is a generic mock for trying the stack without
another service. Start the stack and send a request through the proxy:

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

The upstream must be resolvable and reachable from the NGINX container. For a
service in another Compose project or a standalone container, attach it and
the mirror to a shared Docker network.

## Compose services

- `mirror` — NGINX reverse proxy, published on `LISTEN_HOST:LISTEN_PORT`.
- `sapodilla` — Go REST API; its host port is bound to loopback only.
- `echo-api` — local generic echo service for development and tests.

## Configuration

Compose passes these variables into the containers. Unset or empty values use
the defaults below.

| Variable | Meaning | Default |
| --- | --- | --- |
| `LISTEN_HOST` | Host address used to publish the proxy port | `0.0.0.0` |
| `LISTEN_PORT` | Proxy port (container and published host port) | `8080` |
| `UPSTREAM_HOST` | API hostname as resolved by NGINX | `echo-api` |
| `UPSTREAM_PORT` | API port; also configures the bundled echo service | `11434` |
| `SAPODILLA_HOST` | Go API hostname as resolved by NGINX | `sapodilla` |
| `SAPODILLA_PORT` | Go API port used by NGINX and Compose | `9090` |
| `ADDR` | Go API listen address; Compose derives it from `SAPODILLA_PORT` unless set | `:9090` |

For the Sapodilla binary, precedence is **`-addr` flag > `ADDR` environment
variable > `:9090` default**. In Compose, if you set `ADDR` yourself, keep its
port in sync with `SAPODILLA_PORT`; the flag is mainly useful for direct binary
or container runs.

## Run the images directly

The Sapodilla container must be on the same Docker network as the proxy. These
commands build the images and run Sapodilla and the proxy on a shared network;
replace `my-api:3000` with a reachable service name and port:

```sh
docker network create usage-mirror
docker build -t sapodilla:local -f Dockerfile.sapodilla .
docker build -t web-api-mirror:local -f Dockerfile.mirror .

docker run -d --name sapodilla --network usage-mirror \
  -p 127.0.0.1:9090:9090 -e ADDR=:9090 sapodilla:local

docker run -d --name mirror --network usage-mirror -p 0.0.0.0:9000:9000 \
  -e LISTEN_PORT=9000 \
  -e UPSTREAM_HOST=my-api -e UPSTREAM_PORT=3000 \
  -e SAPODILLA_HOST=sapodilla -e SAPODILLA_PORT=9090 web-api-mirror:local
```

## Sapodilla API

- `GET /api/healthz` — liveness check.
- `POST /track` — metadata-only request mirror target used by NGINX.
- `GET /api/usage` — returns `{ "total": number, "last_seen": epoch_milliseconds, "last_seen_datetime": rfc3339_datetime }`. Before the first tracked request, both timestamps represent when Sapodilla started.

The counter is in memory and resets when Sapodilla restarts. Sapodilla is
published on loopback by the Compose setup; the proxy itself is published
on `LISTEN_HOST`.

## Development

Run the Go API tests from its module root with `cd sapodilla && go test ./...`.
The Docker Compose integration suite runs from the repository root with
`python -m pytest -q`; it selects non-default ports to exercise the environment
variable configuration path.
