#!/usr/bin/env bash
# Run TP-Link poll benchmark inside the collector container (no DB writes).
# Usage: from repo root, with stack up: ./scripts/run_benchmark_poll.sh [--sweep] [extra args...]

set -euo pipefail
cd "$(dirname "$0")/.."

EXTRA=("$@")
if [[ ${#EXTRA[@]} -eq 0 ]]; then
  EXTRA=(--rounds 5)
fi

if ! docker compose ps collector 2>/dev/null | grep -q "Up"; then
  echo "Collector container is not running. Start with: docker compose up -d collector"
  exit 1
fi

exec docker compose exec collector python /app/benchmark_poll_cycle.py "${EXTRA[@]}"
