#!/usr/bin/env bash
# Helper for testing the LEM field ingest API against a local REM stack.
#
#   ./scripts/field_test.sh setup    # create a test experiment + print a LEM join code
#   ./scripts/field_test.sh verify   # show what has landed in gos_rem
#   ./scripts/field_test.sh cleanup  # remove the test experiment + token
#
# Env overrides:
#   BASE_URL   (default http://localhost:7001)   REM admin base URL
#   EXP_NAME   (default "LEM Field Test")         experiment name
#   ADMIN_BASIC_USER / ADMIN_BASIC_PASSWORD       set if you enabled basic auth
#   DB_CONTAINER (default stats-timescaledb)      timescaledb container name
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:7001}"
EXP_NAME="${EXP_NAME:-LEM Field Test}"
EXP_ID="$(printf '%s' "$EXP_NAME" | tr '[:upper:] _' '[:lower:]--')"
DB_CONTAINER="${DB_CONTAINER:-stats-timescaledb}"

AUTH=()
if [[ -n "${ADMIN_BASIC_USER:-}" ]]; then
  AUTH=(-u "${ADMIN_BASIC_USER}:${ADMIN_BASIC_PASSWORD}")
fi

case "${1:-}" in
  setup)
    now="$(python3 -c 'from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat())')"
    echo "Creating experiment '$EXP_NAME' (id: $EXP_ID), current from $now ..."
    curl -fsS "${AUTH[@]}" -X POST "$BASE_URL/api/experiments" \
      --data-urlencode "name=$EXP_NAME" \
      --data-urlencode "is_current=true" \
      --data-urlencode "start_time=$now" \
      --data-urlencode "target_cadence_s=10" >/dev/null || \
      echo "  (experiment may already exist — continuing)"
    echo "Minting a field join code ..."
    resp="$(curl -fsS "${AUTH[@]}" -X POST "$BASE_URL/api/experiments/$EXP_ID/field-token")"
    code="$(printf '%s' "$resp" | python3 -c 'import sys,json; print(json.load(sys.stdin)["join_code"])')"
    echo
    echo "  Join code (paste into LEM):"
    echo "    $code"
    echo
    echo "  Then in LEM:  lem rem join $code"
    echo "                lem --plugs fake1 --duration 60s --interval 5"
    ;;

  verify)
    echo "Rows in gos_rem by alias:"
    docker exec "$DB_CONTAINER" psql -U "${POSTGRES_USER:-gos}" -d "${POSTGRES_DB:-gos_rem}" -c \
      "SELECT alias, count(*) AS rows, min(time) AS first, max(time) AS last
       FROM gos_rem GROUP BY alias ORDER BY rows DESC;"
    echo
    echo "Field upload status (server-side):"
    curl -fsS "${AUTH[@]}" "$BASE_URL/api/experiments/$EXP_ID/field" | python3 -m json.tool
    ;;

  cleanup)
    curl -fsS "${AUTH[@]}" -X DELETE "$BASE_URL/api/experiments/$EXP_ID/field-token" >/dev/null || true
    curl -fsS "${AUTH[@]}" -X DELETE "$BASE_URL/api/experiments/$EXP_ID" >/dev/null || true
    echo "Removed test experiment '$EXP_ID' and its field token."
    echo "(Measurement rows stay in gos_rem; drop them with:"
    echo "  docker exec $DB_CONTAINER psql -U ${POSTGRES_USER:-gos} -d ${POSTGRES_DB:-gos_rem} -c \\"
    echo "    \"DELETE FROM gos_rem WHERE alias IN ('fake1','Lyon TV');\" )"
    ;;

  *)
    echo "usage: $0 {setup|verify|cleanup}" >&2
    exit 1
    ;;
esac
