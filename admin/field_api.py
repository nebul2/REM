"""Field ingest API — lets LEM (Local Energy Measurement) instances stream
locally-measured power data into REM experiments.

Design (see LEM repo docs): identity is the Tapo nickname, exactly as the
cloud collector uses it, so local and cloud data merge per-plug. Access is a
per-experiment bearer token, handed to volunteers inside a pasteable join
code. Uploaded aliases are auto-added to a "field-<experiment>" group linked
to the experiment, so exports and focus resolution include them with no
operator action. While uploads are arriving, field_sessions.json marks the
covered aliases; the collector skips cloud-polling those until the entries
expire (TTL renewed by each upload) — saving TP-Link API calls.

Endpoints under /api/field/* are exempt from admin basic auth (they carry
their own token); the operator endpoints for managing tokens live under
/api/experiments/* and keep normal admin auth.

All endpoints are sync `def`s: FastAPI runs them in its threadpool, and a
module lock serialises JSON read-modify-write against other field requests.
"""

import base64
import json
import secrets
import threading
from datetime import datetime, timedelta, timezone

import device_registry
from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import JSONResponse
from psycopg2.extras import execute_values

router = APIRouter()

SESSION_TTL_S = 90
MAX_BATCH_ROWS = 10000
JOIN_CODE_PREFIX = "REM1-"

_lock = threading.Lock()
_cfg: dict = {}


def configure(*, data_dir, get_db_connection, load_groups, save_groups,
              load_experiments, save_experiments, public_url=""):
    """Late wiring from app.py (avoids a circular import)."""
    _cfg.update(
        data_dir=data_dir,
        get_db_connection=get_db_connection,
        load_groups=load_groups,
        save_groups=save_groups,
        load_experiments=load_experiments,
        save_experiments=save_experiments,
        public_url=public_url.rstrip("/"),
    )


def _path(name):
    return _cfg["data_dir"] / name


def _load_json(name, default):
    try:
        with open(_path(name), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(name, payload):
    device_registry._atomic_write_json(_path(name), payload)


def _now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Token auth
# ---------------------------------------------------------------------------

def _auth_experiment(request: Request) -> str:
    """Validate the bearer token; return the experiment_id it belongs to."""
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    tokens = _load_json("field_tokens.json", {})
    for experiment_id, entry in tokens.items():
        if secrets.compare_digest(token, entry.get("token", "")):
            return experiment_id
    raise HTTPException(status_code=401, detail="Invalid or revoked field token")


def _get_experiment_or_410(experiment_id: str) -> dict:
    experiment = _cfg["load_experiments"]().get(experiment_id)
    if experiment is None:
        raise HTTPException(
            status_code=410,
            detail=f"Experiment '{experiment_id}' no longer exists on this REM",
        )
    return experiment


def _experiment_summary(experiment: dict) -> dict:
    return {
        "id": experiment.get("id"),
        "name": experiment.get("name"),
        "is_current": bool(experiment.get("is_current")),
        "target_cadence_s": experiment.get("target_cadence_s", 10),
    }


def _common_ack_fields(experiment: dict) -> dict:
    return {
        "target_cadence_s": experiment.get("target_cadence_s", 10),
        "is_current": bool(experiment.get("is_current")),  # is the experiment recording?
        "server_time": _now().isoformat(),
        "session_ttl_s": SESSION_TTL_S,
        "max_batch_rows": MAX_BATCH_ROWS,
    }


# ---------------------------------------------------------------------------
# Session + grouping + status bookkeeping (called under _lock)
# ---------------------------------------------------------------------------

def _renew_sessions(aliases, experiment_id):
    data = _load_json("field_sessions.json", {})
    sessions = data.get("aliases") or {}
    now = _now()
    expires = (now + timedelta(seconds=SESSION_TTL_S)).isoformat()
    for alias in aliases:
        sessions[alias] = {"expires_at": expires, "experiment_id": experiment_id}
    # Prune expired entries so the file can't grow without bound
    def alive(info):
        try:
            return datetime.fromisoformat(info["expires_at"]) > now
        except Exception:
            return False
    data["aliases"] = {a: i for a, i in sessions.items() if alive(i)}
    data["updated_at"] = now.isoformat()
    _save_json("field_sessions.json", data)


def _ensure_field_group(experiment_id, aliases):
    """Group uploaded aliases under field-<experiment> and link it to the
    experiment, so exports/focus include field data automatically."""
    if not aliases:
        return
    group_name = f"field-{experiment_id}"
    now_iso = _now().isoformat()

    groups = _cfg["load_groups"]()
    group = groups.get(group_name)
    changed = group is None
    if group is None:
        group = {"name": group_name, "devices": [], "created_at": now_iso}
    for alias in aliases:
        if alias not in group["devices"]:
            group["devices"].append(alias)
            changed = True
    if changed:
        group["updated_at"] = now_iso
        groups[group_name] = group
        _cfg["save_groups"](groups)

    experiments = _cfg["load_experiments"]()
    experiment = experiments.get(experiment_id)
    if experiment is not None and group_name not in experiment.get("linked_groups", []):
        experiment.setdefault("linked_groups", []).append(group_name)
        experiment["updated_at"] = now_iso
        _cfg["save_experiments"](experiments)


def _update_status(experiment_id, batch_id, per_alias_rows):
    status = _load_json("field_status.json", {})
    entry = status.setdefault(experiment_id, {"aliases": {}})
    entry["last_batch_id"] = batch_id
    now_iso = _now().isoformat()
    for alias, count in per_alias_rows.items():
        alias_entry = entry["aliases"].setdefault(alias, {"rows_total": 0})
        alias_entry["rows_total"] += count
        alias_entry["last_upload_at"] = now_iso
    status["updated_at"] = now_iso
    _save_json("field_status.json", status)


# ---------------------------------------------------------------------------
# Volunteer endpoints (bearer token; exempt from admin basic auth)
# ---------------------------------------------------------------------------

@router.post("/api/field/hello")
def field_hello(request: Request, payload: dict = Body(default={})):
    experiment_id = _auth_experiment(request)
    experiment = _get_experiment_or_410(experiment_id)
    return JSONResponse(content={
        "ok": True,
        "experiment": _experiment_summary(experiment),
        **_common_ack_fields(experiment),
    })


@router.post("/api/field/batch")
def field_batch(request: Request, payload: dict = Body(...)):
    experiment_id = _auth_experiment(request)
    experiment = _get_experiment_or_410(experiment_id)

    batch_id = str(payload.get("batch_id") or "")
    covering = [str(a) for a in (payload.get("covering") or [])]
    rows = payload.get("rows") or []
    if not batch_id:
        raise HTTPException(status_code=400, detail="batch_id is required")
    if len(rows) > MAX_BATCH_ROWS:
        raise HTTPException(status_code=413, detail=f"Batch exceeds {MAX_BATCH_ROWS} rows")

    # Idempotent retry: a client re-sending the batch whose ack it lost gets
    # a duplicate ack and no second insert.
    with _lock:
        status = _load_json("field_status.json", {})
        if status.get(experiment_id, {}).get("last_batch_id") == batch_id:
            return JSONResponse(content={
                "ok": True, "inserted": 0, "duplicate": True,
                **_common_ack_fields(experiment),
            })

    # Parse and validate the whole batch before touching the DB — a bad row
    # rejects the batch atomically (the client's CSV is the recovery path).
    values = []
    per_alias_rows: dict = {}
    for i, row in enumerate(rows):
        try:
            ts_raw, alias, watts = row[0], str(row[1]), float(row[2])
            ts = datetime.fromisoformat(str(ts_raw))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Bad row {i}: {e}")
        values.append((ts, alias, watts))
        per_alias_rows[alias] = per_alias_rows.get(alias, 0) + 1

    inserted = 0
    if values:
        conn = _cfg["get_db_connection"]()
        try:
            cursor = conn.cursor()
            execute_values(
                cursor,
                "INSERT INTO gos_rem (time, alias, power_watts) VALUES %s",
                values,
            )
            conn.commit()
            cursor.close()
            inserted = len(values)
        finally:
            conn.close()

    with _lock:
        _renew_sessions(set(covering) | set(per_alias_rows), experiment_id)
        _ensure_field_group(experiment_id, sorted(per_alias_rows))
        _update_status(experiment_id, batch_id, per_alias_rows)

    return JSONResponse(content={
        "ok": True, "inserted": inserted, "duplicate": False,
        **_common_ack_fields(experiment),
    })


@router.get("/api/field/status")
def field_status(request: Request):
    experiment_id = _auth_experiment(request)
    experiment = _get_experiment_or_410(experiment_id)
    status = _load_json("field_status.json", {}).get(experiment_id, {"aliases": {}})
    sessions = _load_json("field_sessions.json", {}).get("aliases", {})
    now = _now()
    active = {
        a: i for a, i in sessions.items()
        if i.get("experiment_id") == experiment_id
        and datetime.fromisoformat(i["expires_at"]) > now
    }
    return JSONResponse(content={
        "ok": True,
        "experiment": _experiment_summary(experiment),
        "aliases": status.get("aliases", {}),
        "active_sessions": active,
        **_common_ack_fields(experiment),
    })


# ---------------------------------------------------------------------------
# Operator endpoints (normal admin basic auth — NOT under /api/field)
# ---------------------------------------------------------------------------

def _join_code(request: Request, experiment_id: str, token: str) -> str:
    url = _cfg.get("public_url") or str(request.base_url).rstrip("/")
    blob = json.dumps({"u": url, "e": experiment_id, "t": token})
    return JOIN_CODE_PREFIX + base64.urlsafe_b64encode(blob.encode()).decode()


# Unambiguous alphabet (no 0/O/1/I/L) for short codes texted/read aloud.
_SHORT_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def _new_short_code(tokens: dict) -> str:
    taken = {e.get("short_code") for e in tokens.values()}
    while True:
        code = "".join(secrets.choice(_SHORT_ALPHABET) for _ in range(6))
        if code not in taken:
            return code


@router.post("/api/experiments/{experiment_id}/field-token")
def create_field_token(experiment_id: str, request: Request):
    """Create (or rotate — the old code stops working) the experiment's
    field token, and return both the self-contained join code and a short
    code (for texting; resolved via /api/field/resolve against the server)."""
    _get_experiment_or_410(experiment_id)
    with _lock:
        tokens = _load_json("field_tokens.json", {})
        tokens[experiment_id] = {
            "token": secrets.token_urlsafe(24),
            "short_code": _new_short_code(tokens),
            "created_at": _now().isoformat(),
        }
        _save_json("field_tokens.json", tokens)
    entry = tokens[experiment_id]
    return JSONResponse(content={
        "success": True,
        "experiment_id": experiment_id,
        "join_code": _join_code(request, experiment_id, entry["token"]),
        "short_code": entry["short_code"],
        "created_at": entry["created_at"],
    })


@router.get("/api/field/resolve/{code}")
def field_resolve(code: str, request: Request):
    """Resolve a short code to full join info (token-less endpoint — the short
    code IS the shared secret, same trust as the long join code)."""
    code = code.strip().upper()
    tokens = _load_json("field_tokens.json", {})
    for eid, entry in tokens.items():
        if (entry.get("short_code") or "").upper() == code:
            return JSONResponse(content={
                "url": _cfg.get("public_url") or str(request.base_url).rstrip("/"),
                "experiment_id": eid,
                "token": entry["token"],
            })
    raise HTTPException(status_code=404, detail="Unknown or rotated short code")


@router.get("/api/experiments/{experiment_id}/field")
def get_field_info(experiment_id: str, request: Request):
    """Operator view: token presence + join code + upload/session status."""
    _get_experiment_or_410(experiment_id)
    tokens = _load_json("field_tokens.json", {})
    entry = tokens.get(experiment_id)
    status = _load_json("field_status.json", {}).get(experiment_id, {"aliases": {}})
    sessions = _load_json("field_sessions.json", {}).get("aliases", {})
    now = _now()
    active = {
        a: i for a, i in sessions.items()
        if i.get("experiment_id") == experiment_id
        and datetime.fromisoformat(i["expires_at"]) > now
    }
    return JSONResponse(content={
        "success": True,
        "token": {
            "exists": entry is not None,
            "created_at": entry["created_at"] if entry else None,
            "join_code": _join_code(request, experiment_id, entry["token"]) if entry else None,
            "short_code": entry.get("short_code") if entry else None,
        },
        "uploads": status.get("aliases", {}),
        "active_sessions": active,
    })


@router.delete("/api/experiments/{experiment_id}/field-token")
def revoke_field_token(experiment_id: str):
    with _lock:
        tokens = _load_json("field_tokens.json", {})
        existed = tokens.pop(experiment_id, None) is not None
        _save_json("field_tokens.json", tokens)
    return JSONResponse(content={"success": True, "revoked": existed})
