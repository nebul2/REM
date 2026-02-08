#!/usr/bin/env bash
# Get a new TP-Link refresh token so the stats collector can list devices.
# Run from your Mac (or any machine with a browser). You'll paste the code into the terminal.
#
# Steps:
# 1. Open the URL below in your browser and sign in to TP-Link / Kasa.
# 2. After authorizing, you're redirected to greeningofstreaming.org?code=XXXX
#    Copy the "code" value (the XXXX part).
# 3. Run this script - it will prompt for the code, then exchange it for tokens
#    and show you what to put in .env and (optionally) how to update pi400.

set -e

AUTH_URL="https://aps1-openapi.tplinknbu.com/v1/oauth/authorize?client_id=fdcae128-0adf-4233-8a58-30760652bd16&response_type=code&scope=all&state=123456789012345678901234&redirect_uri=https://www.greeningofstreaming.org"
TOKEN_URL="https://aps1-openapi.tplinknbu.com/v1/oauth/token"
CLIENT_ID="fdcae128-0adf-4233-8a58-30760652bd16"
CLIENT_SECRET="4087d4b9-5e0c-4e50-b06c-22580fc618d5"

echo "=== TP-Link OAuth – get refresh token for stats collector ==="
echo ""
echo "1. Open this URL in your browser (sign in to TP-Link/Kasa if asked):"
echo ""
echo "   $AUTH_URL"
echo ""
echo "2. After authorizing, you'll be redirected to a URL like:"
echo "   https://www.greeningofstreaming.org?code=XXXXXXXX"
echo "   Copy the 'code' value (the XXXXXXXXX part)."
echo ""
read -p "3. Paste the code here: " CODE
if [[ -z "$CODE" ]]; then
  echo "No code entered. Exiting."
  exit 1
fi

echo ""
echo "Exchanging code for tokens..."
RESP=$(curl -sS -X POST "$TOKEN_URL" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "grant_type=code" \
  -d "code=$CODE")

if echo "$RESP" | grep -q "accessToken"; then
  REFRESH=$(echo "$RESP" | python3 -c "import sys, json; print(json.load(sys.stdin).get('refreshToken', ''))")
  if [[ -n "$REFRESH" ]]; then
    echo ""
    echo "✅ Success. Your refresh token:"
    echo ""
    echo "$REFRESH"
    echo ""
    echo "--- What to do next ---"
    echo ""
    echo "A) Update .env on pi400 (and in this repo if you track it):"
    echo "   TPLINK_REFRESH_TOKEN=$REFRESH"
    echo ""
    echo "B) On pi400: edit /home/d2/stats/.env and set:"
    echo "   TPLINK_REFRESH_TOKEN=<paste the token above>"
    echo "   Then recreate collector (restart does not reload .env):"
    echo "   ssh pi400 'cd /home/d2/stats && sudo docker compose up -d collector'"
    echo ""
    echo "C) After restart, open the stats admin UI – devices should list (if your plugs are online)."
  else
    echo "Could not parse refreshToken from response."
    echo "$RESP"
    exit 1
  fi
else
  echo "Token exchange failed. Response:"
  echo "$RESP"
  exit 1
fi
