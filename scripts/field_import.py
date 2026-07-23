#!/usr/bin/env python3
"""Hand-import a LEM run into a REM experiment, e.g. a CSV received after the
event. Reuses the field API — no special DB access needed.

  python3 scripts/field_import.py <rem_csv> <experiment_id> [--url URL] [--extend]

The CSV must be a LEM "REM-ready" file (timestamp,alias,power_w where alias is
the Tapo nickname) — produce it with `lem rem export`. A plain _combined.csv
uses local aliases and won't match REM identity.

Auth: admin basic auth via ADMIN_BASIC_USER / ADMIN_BASIC_PASSWORD env
(needed to mint a field token). --extend moves the experiment's end time to
cover the imported rows, so late data falls inside the export window.
"""
import argparse
import base64
import csv
import json
import os
import sys
import urllib.parse
import urllib.request

BATCH = 5000


def _auth_header(token=None):
    if token:
        return {"Authorization": f"Bearer {token}"}
    u, p = os.environ.get("ADMIN_BASIC_USER", ""), os.environ.get("ADMIN_BASIC_PASSWORD", "")
    if u:
        return {"Authorization": "Basic " + base64.b64encode(f"{u}:{p}".encode()).decode()}
    return {}


def _req(method, url, json_body=None, form=None, token=None):
    headers = _auth_header(token)
    if json_body is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(json_body).encode()
    elif form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        body = urllib.parse.urlencode(form).encode()
    else:
        body = None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("experiment_id")
    ap.add_argument("--url", default="http://localhost:7001")
    ap.add_argument("--extend", action="store_true",
                    help="move the experiment end time to cover the imported rows")
    args = ap.parse_args()

    rows, max_ts = [], ""
    with open(args.csv) as f:
        r = csv.reader(f)
        header = next(r, None)
        for row in r:
            if len(row) == 3:
                rows.append([row[0], row[1], float(row[2])])
                max_ts = max(max_ts, row[0])
    if not rows:
        sys.exit("No rows in CSV.")

    tok = _req("POST", f"{args.url}/api/experiments/{args.experiment_id}/field-token")
    token = json.loads(base64.urlsafe_b64decode(tok["join_code"][5:]))["t"]

    total = 0
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        ack = _req("POST", f"{args.url}/api/field/batch",
                   json_body={"batch_id": f"import-{i}", "covering": [], "rows": chunk}, token=token)
        total += ack.get("inserted", 0)
    print(f"Imported {total} rows into experiment '{args.experiment_id}'.")

    if args.extend:
        _req("PUT", f"{args.url}/api/experiments/{args.experiment_id}",
             form={"end_time": max_ts})
        print(f"Extended experiment end time to {max_ts}.")
    else:
        print("Note: if the experiment has ended, re-run with --extend so these "
              "rows fall inside its export window.")


if __name__ == "__main__":
    main()
