#!/bin/bash

cd "$(dirname "$0")/.."

docker compose up -d --build

echo "Sandoghchi API running"

