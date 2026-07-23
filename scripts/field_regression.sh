#!/usr/bin/env bash
# Regression check: confirm the field-api branch didn't break existing REM.
# Run after: git pull && docker compose up -d --build admin
#
#   ./scripts/field_regression.sh
#
# Env: BASE_URL (default http://localhost:7001);
#      ADMIN_BASIC_USER / ADMIN_BASIC_PASSWORD if basic auth is enabled.
set -u
BASE_URL="${BASE_URL:-http://localhost:7001}"
AUTH=()
[[ -n "${ADMIN_BASIC_USER:-}" ]] && AUTH=(-u "${ADMIN_BASIC_USER}:${ADMIN_BASIC_PASSWORD}")

pass=0; fail=0
chk() {  # chk "label" expected_code curl-args...
  local label="$1" want="$2"; shift 2
  local code; code=$(curl -s -o /dev/null -w '%{http_code}' "$@")
  if [[ "$code" == "$want" ]]; then echo "  ok   $label ($code)"; pass=$((pass+1))
  else echo "  FAIL $label (got $code, want $want)"; fail=$((fail+1)); fi
}

echo "== existing endpoints still work =="
chk "GET /api/experiments" 200 "${AUTH[@]+"${AUTH[@]}"}" "$BASE_URL/api/experiments"
chk "GET /api/groups"      200 "${AUTH[@]+"${AUTH[@]}"}" "$BASE_URL/api/groups"
chk "GET / (admin UI)"     200 "${AUTH[@]+"${AUTH[@]}"}" "$BASE_URL/"
chk "GET /health"          200 "$BASE_URL/health"

echo "== field API mounted, own auth =="
chk "POST /api/field/hello no token -> 401" 401 -X POST "$BASE_URL/api/field/hello"

if [[ -n "${ADMIN_BASIC_USER:-}" ]]; then
  echo "== basic auth still guards non-field paths =="
  chk "GET /api/experiments no creds -> 401" 401 "$BASE_URL/api/experiments"
  chk "field path exempt from basic auth -> 401 (token, not basic)" 401 -X POST "$BASE_URL/api/field/hello"
else
  echo "== basic auth disabled (ADMIN_BASIC_USER unset) — skipping auth checks =="
fi

echo
echo "Result: $pass passed, $fail failed"
[[ $fail -eq 0 ]] || exit 1
