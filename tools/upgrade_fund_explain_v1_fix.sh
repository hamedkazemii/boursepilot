#!/usr/bin/env bash
set -e

echo "🚀 Fix Fund Explain v1 import path"

cd "$(dirname "$0")/.."

export PYTHONPATH="$PWD:$PYTHONPATH"

echo "🧪 testing..."

python tools/test_explain.py سیگلو یاقوت رشد اهرم

echo "✅ Fund Explain v1 fixed"
