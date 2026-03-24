#!/usr/bin/env bash
# Safe production deploy for Akamai Linode (or any host using this compose stack).
#
# Run ON THE SERVER from the stats repo directory (e.g. ~/stats or /opt/stats):
#   chmod +x scripts/deploy-linode.sh
#   ./scripts/deploy-linode.sh
#
# What it does:
#   - Optional: git pull (if this is a git checkout)
#   - docker compose build / up -d — refreshes images and containers
#   - NEVER runs "docker compose down -v" (volumes = your TimescaleDB + admin JSON data)
#
# What was missing in-repo before: DevBench used .devbench/scripts/deploy.sh for pi400;
# that path lives outside this repo. This script is the in-tree equivalent for Linode.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE=(docker compose)
if ! docker compose version &>/dev/null; then
  COMPOSE=(docker-compose)
fi

echo "==> GOS REM deploy (data-safe: no volume removal)"
echo "    Directory: $ROOT"

if [[ -d .git ]] && command -v git &>/dev/null; then
  echo "==> git pull (optional; rsync/scp deploys often have no GitHub access)"
  git pull || echo "    (continuing: git pull failed or unavailable — using files on disk)"
else
  echo "==> (skip git pull: not a git clone or git missing)"
fi

echo "==> ${COMPOSE[*]} build"
"${COMPOSE[@]}" build

echo "==> ${COMPOSE[*]} up -d"
"${COMPOSE[@]}" up -d

echo "==> ${COMPOSE[*]} ps"
"${COMPOSE[@]}" ps

echo "==> Done. Volumes unchanged (timescaledb-data, admin-data, collector-data, …)."
