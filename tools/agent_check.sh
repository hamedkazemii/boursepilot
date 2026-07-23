#!/bin/bash

set -e

cd "$(dirname "$0")/.."

echo "=== Agent Verification ==="

python tools/project_check.py

python - <<'PY'
import os,sys
sys.path.insert(0,os.getcwd())

import api
import core
import services
import reports

from fastapi.testclient import TestClient
from api.main import app

client=TestClient(app)

r=client.get("/api/v1/health")

assert r.status_code==200

routes=[x.path for x in app.routes]

for path in [
"/api/v1/health",
"/api/v1/ranking/today",
"/api/v1/funds/{symbol}",
"/api/v1/me/portfolio"
]:
    assert path in routes,path

print("IMPORT OK")
print("API OK")
print("ROUTES OK")
PY

echo "AGENT READY"
