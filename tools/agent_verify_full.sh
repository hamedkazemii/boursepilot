#!/bin/bash

set -e

cd "$(dirname "$0")/.."

echo "=== Sandoghchi Verification ==="

python - <<'PY'
import api
import core
import services
import reports
print("IMPORT OK")
PY

python - <<'PY'
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

routes=[r.path for r in app.routes]

assert "/api/v1/health" in routes
assert "/api/v1/ranking/today" in routes

r=client.get("/api/v1/health")

assert r.status_code==200

print("ROUTES OK")
print("HEALTH OK")
PY

test -f AGENT.md
test -f docs/MASTER_CONTEXT.md
test -f docs/PROJECT_STATE.md

echo "DOCUMENTATION OK"

echo "=== AGENT READY ==="
