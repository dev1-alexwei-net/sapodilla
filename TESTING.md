# Testing

The repository contains a Go usage sidecar, a generic Python echo upstream for
local integration runs, and a Docker Compose NGINX proxy. The test path does not
require Ollama or a live external API.

## Prerequisites

- Go 1.23 or newer for sidecar tests.
- Python 3.9 or newer, pytest, and requests: `python -m pip install 'pytest>=7' 'requests>=2.28'`.
- Docker Engine and Docker Compose v2 for tests that start the Compose stack.

## Run checks locally

Run the sidecar unit tests from its module directory:

```sh
cd sidecar
go test ./...
```

Run the Python suite from the repository root:

```sh
python -m pytest -q
```

Go unit tests cover the store, tracker, and usage handler. Compose integration
tests start the proxy, sidecar, and bundled echo upstream with non-default
ports, then verify request passthrough, mirrored usage counts, and passthrough
while the sidecar is stopped. Pytest tears down the Compose stack afterward.

To run the end-to-end smoke script manually:

```sh
docker compose up --build -d
./scripts/smoke.sh
docker compose down
```

Set `LISTEN_PORT` and `SIDECAR_PORT` consistently for both Compose and the
smoke script when using non-default ports.

## Continuous integration

Pull requests to `main` run:

- Go formatting, `go vet`, and race-enabled Go unit tests.
- The pytest suite, including Compose-backed integration tests.
- Docker builds for the sidecar, NGINX proxy, and mock upstream.
- A Docker Compose smoke flow using non-default proxy, sidecar, and upstream
  ports.
- Ruff lint/format checks and SonarCloud analysis.

The GHCR multi-architecture publish jobs run on pushes to `main`, not on pull
requests.
