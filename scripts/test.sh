#!/usr/bin/env bash
set -euo pipefail

compose=(docker compose --file docker-compose.test.yaml)

cleanup() {
    "${compose[@]}" down --volumes --remove-orphans
}

trap cleanup EXIT

"${compose[@]}" up --build --abort-on-container-exit --exit-code-from test
