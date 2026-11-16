# Testing

The repository contains a Go usage API, a generic Python echo API for local
integration runs, and a Docker Compose NGINX proxy. Tests do not require Ollama
or a live external API.

## Prerequisites

- Go 1.23 or newer for usage API tests.
- Python 3.9 or newer, pytest, and requests: `python -m pip install 'pytest>=7' 'requests>=2.28'`.
- Docker Engine and Docker Compose v2 for tests that start the Compose stack.

## Run checks locally

Run black-box Go tests from the nested module root:

```sh
cd ollama-mirror
go test -race ./...
```

Run the Python suite from the repository root:

```sh
python -m pytest -q
```

The Go tests build and start the usage API, then verify its health and REST
behavior, including concurrent tracking. Compose integration tests start the
proxy, usage API, and bundled echo API with non-default ports, then verify
request passthrough, mirrored usage counts, and that the usage API host port is
loopback-only. Pytest tears down the Compose stack afterward.

To run the end-to-end smoke script manually:

```sh
docker compose up --build -d
./scripts/smoke.sh
docker compose down
```

Set `LISTEN_PORT` and `USAGE_API_PORT` consistently for both Compose and the
smoke script when using non-default ports.

## Continuous integration

Pull requests to `main` run:

- Go formatting, `go vet`, and race-enabled Go tests.
- The pytest suite, including Compose-backed integration tests.
- Docker builds for the usage API, NGINX mirror, and echo API.
- A Docker Compose smoke flow using non-default proxy, usage API, and upstream
  ports.
- Ruff lint/format checks and SonarCloud analysis.

The GHCR multi-architecture publish jobs run on pushes to `main`, not on pull
requests.
