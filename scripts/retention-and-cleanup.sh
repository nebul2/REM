#!/usr/bin/env bash
# Run on the Pi400 (or wherever stats stack runs) to:
# - Report current TimescaleDB size and row count
# - Optionally delete data older than 90 days and reclaim space
# - Add 90-day retention policy if not already present
#
# Usage: from the stats project root (e.g. ~/stats): ./scripts/retention-and-cleanup.sh
# Or: bash /path/to/retention-and-cleanup.sh (from project root)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

COMPOSE_CMD="docker compose"
if ! docker compose version &>/dev/null; then
  COMPOSE_CMD="docker-compose"
fi

CONTAINER="$($COMPOSE_CMD ps -q timescaledb 2>/dev/null || true)"
if [ -z "$CONTAINER" ]; then
  echo "TimescaleDB container not running. Start the stack with: $COMPOSE_CMD up -d"
  exit 1
fi

PSQL="docker compose exec -T timescaledb psql -U gos -d gos_rem"
[ "$COMPOSE_CMD" = "docker-compose" ] && PSQL="docker-compose exec -T timescaledb psql -U gos -d gos_rem"

echo "=== Current database size and range ==="
$COMPOSE_CMD exec -T timescaledb psql -U gos -d gos_rem -t -c "
  SELECT 'Database size: ' || pg_size_pretty(pg_database_size('gos_rem'));
  SELECT 'Rows: ' || COUNT(*) FROM gos_rem;
  SELECT 'Oldest: ' || MIN(time)::text || '  Newest: ' || MAX(time)::text FROM gos_rem;
"

echo ""
echo "=== Retention policy ==="
POLICY="$($COMPOSE_CMD exec -T timescaledb psql -U gos -d gos_rem -t -c "
  SELECT job_id FROM timescaledb_information.jobs j
  JOIN timescaledb_information.hypertables h ON j.hypertable_name = h.hypertable_name
  WHERE h.hypertable_name = 'gos_rem' AND j.proc_name = 'policy_retention' LIMIT 1;
" 2>/dev/null | tr -d ' \n')"
if [ -n "$POLICY" ]; then
  echo "A 90-day retention policy is already in place."
else
  echo "Adding 90-day retention policy..."
  $COMPOSE_CMD exec -T timescaledb psql -U gos -d gos_rem -c "
    SELECT add_retention_policy('gos_rem', INTERVAL '90 days');
  " && echo "Done. Old data will be dropped automatically from now on."
fi

echo ""
read -p "Delete existing data older than 90 days now and reclaim space? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[yY]$ ]]; then
  echo "Deleting old data..."
  $COMPOSE_CMD exec -T timescaledb psql -U gos -d gos_rem -c "
    DELETE FROM gos_rem WHERE time < NOW() - INTERVAL '90 days';
  "
  echo "Reclaiming space (VACUUM FULL)..."
  $COMPOSE_CMD exec -T timescaledb psql -U gos -d gos_rem -c "VACUUM FULL gos_rem;"
  echo "Done. Current size:"
  $COMPOSE_CMD exec -T timescaledb psql -U gos -d gos_rem -t -c "
    SELECT pg_size_pretty(pg_database_size('gos_rem')) AS db_size;
  "
fi
