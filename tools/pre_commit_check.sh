#!/bin/bash
set -e

cd "$(dirname "$0")/.."

echo "=== PRE COMMIT CHECK ==="

git status

echo "Compile..."
python -m compileall api core services reports -q
echo "COMPILE OK"

echo "Agent verification..."
bash tools/agent_verify_full.sh

echo "Tests..."
.venv/bin/python -m pytest -q

echo "Docs..."

for f in \
AGENT.md \
docs/AGENT_PROTOCOL.md \
docs/MASTER_CONTEXT.md \
docs/PROJECT_STATE.md \
docs/START_HERE.md
do
    test -f "$f"
done

echo "DOCUMENTATION OK"

echo "=== ALL CHECKS PASSED ==="
