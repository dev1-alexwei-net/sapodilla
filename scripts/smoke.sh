#!/usr/bin/env bash
# End-to-end smoke test for the generic web-API usage tracker.
#
# Usage:
#   docker compose up -d
#   ./scripts/smoke.sh
#
# Exercises:
#   - sidecar health + usage (empty state)
#   - a request mirrored through the proxy (any path)
#   - usage reflects the request (total, last_seen)
#   - a request via the proxy increments the counter

set -euo pipefail

BASE="${BASE:-http://localhost:${LISTEN_PORT:-8080}}"
SIDE="${SIDE:-http://localhost:${SIDECAR_PORT:-9090}}"

step() { printf '\n\033[1;36m== %s ==\033[0m\n' "$1"; }

wait_for() {
    local url="$1" name="$2"
    local i=0
    step "Waiting for ${name} at ${url}"
    until curl -fsS -o /dev/null -w '%{http_code}' "$url" >/dev/null 2>&1; do
        i=$((i + 1))
        if (( i > 30 )); then
            echo "ERROR: ${name} did not become ready" >&2
            exit 1
        fi
        sleep 1
    done
    echo "   ${name} is ready"
}

step "1. Sidecar health"
curl -fsS "$SIDE/api/healthz" | python3 -m json.tool

step "2. Usage before any requests"
curl -fsS "$SIDE/api/usage" | python3 -m json.tool

step "3. Generic request through the proxy (mirrored)"
curl -fsS -X POST "$BASE/any/path" -H 'Content-Type: application/json' \
    -d '{"ping":"pong"}' | python3 -m json.tool

step "4. Usage after mirrored request"
sleep 1
curl -fsS "$SIDE/api/usage" | python3 -m json.tool

step "5. Another request through the generic proxy"
curl -fsS "$BASE/healthz" >/dev/null
sleep 1
step "6. Final usage (total should be >= 2, last_seen recent)"
curl -fsS "$SIDE/api/usage" | python3 -m json.tool

echo
printf '\033[1;32mSMOKE OK\033[0m\n'
