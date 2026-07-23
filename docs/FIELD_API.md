# Field Ingest API (LEM)

REM's field API lets **LEM** (Local Energy Measurement) instances stream
locally-measured power into a REM experiment. It complements the cloud
collector: volunteers who run LEM measure their own plugs over the LAN (no
TP-Link cloud calls) and push the data here, under the **same Tapo nickname**
the collector would use — so local and cloud data for a plug merge seamlessly.

Implemented in [`admin/field_api.py`](../admin/field_api.py); mounted by
`admin/app.py`. Collector integration is in `app/collector.py`.

## Operator runbook

Everything is per-experiment. From the experiments UI or via the API (normal
admin basic auth):

**Create / rotate a join code**
```bash
curl -u admin:PASS -X POST https://stats.example.com/api/experiments/<id>/field-token
# -> { "join_code": "REM1-…", ... }
```
Hand the `REM1-…` code to the volunteer. Rotating issues a new code and
**invalidates the old one**. There is one token per experiment.

**See who's uploading**
```bash
curl -u admin:PASS https://stats.example.com/api/experiments/<id>/field
# -> token presence + join code, per-alias upload counts, active sessions
```

**Revoke access**
```bash
curl -u admin:PASS -X DELETE https://stats.example.com/api/experiments/<id>/field-token
```

Uploaded aliases are automatically added to a group `field-<experiment-id>`
linked to the experiment, so they appear in the experiment's exports and focus
resolution with no further action.

## What the volunteer's LEM does

- `POST /api/field/hello` — validates the token, returns the experiment name
  and `target_cadence_s` (LEM adopts it as its sample interval).
- `POST /api/field/batch` — `{batch_id, covering:[aliases], rows:[[iso_ts, alias, watts], …]}`.
  Rows are inserted into `gos_rem`; `batch_id` makes retries idempotent. Each
  batch renews a 90s **session** for the covered aliases.
- `GET /api/field/status` — per-alias upload totals, for LEM's UI.

Endpoints under `/api/field/*` carry a bearer token and are exempt from admin
basic auth. Behind Traefik, a dedicated auth-free router for `/api/field` is
required (see `docker-compose.traefik.yml`).

## Collector hand-off (saves TP-Link API calls)

While a plug is being measured locally, its alias sits in
`field_sessions.json` with a 90s TTL (renewed by each upload). The collector
reads this file each cycle and **skips cloud-polling covered aliases** — so we
don't hit the TP-Link cloud for plugs LEM already covers (mitigating the risk
of TP-Link throttling or revoking our keys). If a volunteer's LEM stops, the
sessions expire and the collector resumes cloud polling automatically.

## Configuration

- `REM_PUBLIC_URL` (admin env) — the base URL embedded in join codes. Falls
  back to the request URL if unset. Set it to the public HTTPS URL in
  production.
- `SESSION_TTL_S = 90`, `MAX_BATCH_ROWS = 10000` — constants in `field_api.py`.

## Data notes

- Timestamps are client-side UTC ISO 8601, inserted as-is. LEM warns the
  volunteer if their clock differs from the server by >30s.
- `gos_rem` has no uniqueness constraint. If LEM is offline >90s the collector
  resumes cloud polling; a later `lem rem sync` backfill can then add a second
  (equally real) measurement stream for that window. Time-bucketed averaging in
  the UI keeps this sane.
