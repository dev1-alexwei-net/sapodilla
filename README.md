# Generic web-API usage mirror

A small NGINX reverse proxy with a Go sidecar that counts proxied requests. It
forwards any HTTP method, path, query, and body to your API; the sidecar stores
only a total and the time of the latest request. It does not inspect requests.

## Quick start with Docker Compose

The included `upstream` service is a generic echo API for trying the stack
without another service. Start the stack and send a request through the proxy:

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

## Configuration

Compose passes these variables into the containers. Unset or empty values use
the defaults below.

| Variable | Meaning | Default |
| --- | --- | --- |
| `LISTEN_HOST` | Host address used to publish the proxy port | `0.0.0.0` |
| `LISTEN_PORT` | Proxy port (container and published host port) | `8080` |
| `UPSTREAM_HOST` | API hostname as resolved by NGINX | `upstream` |
| `UPSTREAM_PORT` | API port; also configures the bundled echo service | `11434` |
| `SIDECAR_HOST` | Sidecar hostname as resolved by NGINX | `sidecar` |
| `SIDECAR_PORT` | Sidecar port used by NGINX and Compose | `9090` |
| `ADDR` | Go sidecar listen address; Compose derives it from `SIDECAR_PORT` unless set | `:9090` |

For the sidecar binary, precedence is **`-addr` flag > `ADDR` environment
variable > `:9090` default**. In Compose, if you set `ADDR` yourself, keep its
port in sync with `SIDECAR_PORT`; the flag is mainly useful for direct binary
or container runs.

## Run the images directly

The API container must be on the same Docker network as the proxy. These
commands build the images and run the sidecar and proxy on a shared network;
replace `my-api:3000` with a reachable service name and port:

```sh
docker network create mirror
docker build -t web-api-sidecar:local ./sidecar
docker build -t web-api-mirror:local -f nginx/Dockerfile ./nginx

docker run -d --name sidecar --network mirror \
  -p 127.0.0.1:9090:9090 -e ADDR=:9090 web-api-sidecar:local

docker run -d --name api-mirror --network mirror -p 0.0.0.0:9000:9000 \
  -e LISTEN_PORT=9000 \
  -e UPSTREAM_HOST=my-api -e UPSTREAM_PORT=3000 \
  -e SIDECAR_HOST=sidecar -e SIDECAR_PORT=9090 web-api-mirror:local
```

## Sidecar API

- `GET /api/healthz` — liveness check.
- `POST /track` — metadata-only request mirror target used by NGINX.
- `GET /api/usage` — returns `{ "total": number, "last_seen": timestamp|null }`.

The counter is in memory and resets when the sidecar restarts. The sidecar API
is published on loopback by the Compose setup; the proxy itself is published
on `LISTEN_HOST`.

## Development

Run Go unit tests with `cd sidecar && go test ./...`. The Docker Compose
integration suite runs with `pytest`; it selects non-default ports to exercise
the environment-variable configuration path.
