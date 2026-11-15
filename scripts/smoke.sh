#!/usr/bin/env bash
# smoke.sh — end-to-end smoke test for ollama-mirror.
#
# Steps:
#   1. docker compose up -d --build (with mock upstream override)
#   2. wait for nginx to be ready
#   3. GET /api/tags through nginx -> expect 200 + models list
#   4. POST /api/generate through nginx -> expect 200 + SSE
#   5. GET /api/usage on sidecar -> expect total_requests > 0
#   6. docker compose down -v
#
# Exits 0 on success, non-zero on failure.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OVERRIDE="$REPO/tests/mock_upstream/docker-compose.override.yml"

cleanup() {
    echo "[smoke] tearing down..."
    (cd "$REPO" && docker compose -f docker-compose.yml -f "$OVERRIDE" down -v --remove-orphans) \
        >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[smoke] starting compose stack (build + up)..."
(cd "$REPO" && docker compose -f docker-compose.yml -f "$OVERRIDE" up -d --build)

echo "[smoke] waiting for nginx to be ready..."
for i in $(seq 1 60); do
    if curl -fsS http://127.0.0.1:8080/healthz >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

echo "[smoke] SC1: GET /api/tags through proxy"
tags=$(curl -fsS http://127.0.0.1:8080/api/tags)
echo "$tags" | grep -q '"llama3:70b"' || { echo "FAIL: tags missing llama3:70b"; exit 1; }
echo "$tags" | grep -q '"mistral:7b"' || { echo "FAIL: tags missing mistral:7b"; exit 1; }
echo "  OK"

echo "[smoke] SC2: POST /api/generate (SSE) through proxy"
sse=$(curl -fsS -X POST http://127.0.0.1:8080/api/generate \
    -H "Content-Type: application/json" \
    -d '{"model":"llama3:70b","prompt":"hello","stream":true}')
echo "$sse" | grep -q 'data: ' || { echo "FAIL: no SSE data lines"; exit 1; }
echo "$sse" | grep -q '"done":true' || { echo "FAIL: no done marker"; exit 1; }
echo "  OK"

echo "[smoke] SC3: /api/usage reflects requests"
# give the mirror subrequests a moment
sleep 1
usage=$(curl -fsS http://127.0.0.1:9090/api/usage)
echo "$usage" | grep -q '"total_requests":' || { echo "FAIL: no total_requests"; exit 1; }
total=$(echo "$usage" | python3 -c "import sys,json; print(json.load(sys.stdin)['total_requests'])")
if [ "$total" -lt 2 ]; then
    echo "FAIL: total_requests=$total expected >= 2"
    exit 1
fi
echo "  OK (total_requests=$total)"

echo "[smoke] SC8: /api/healthz"
curl -fsS http://127.0.0.1:9090/api/healthz | grep -q '"status":"ok"' || { echo "FAIL: healthz"; exit 1; }
echo "  OK"

echo "[smoke] PASSED"
