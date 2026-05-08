"""
Device Registry — known-fleet state for REM.

The registry is the union of devices the operator has ever known about, with
per-device lifecycle (active/excluded/archived) and status (online/offline/
missing/unknown). It is populated by "Refresh Fleet" actions which call
TP-Link `getDeviceList` via the collector (shape (b): the collector mediates
all TP-Link calls so refresh tokens have a single rotation owner).

File layout on the admin volume:

    {DATA_DIR}/device_registry.json        — the registry itself
    {DATA_DIR}/refresh_fleet_request.json  — admin → collector trigger
    {DATA_DIR}/refresh_fleet_result.json   — collector → admin response

The collector mounts the admin volume at /app/data/admin and reads/writes
these same files there.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REGISTRY_VERSION = 1

# Mirror the collector's allow-list (app/collector.py:390). Devices on the
# TP-Link account whose model is not in this set are silently filtered out
# of refreshes — they cannot deliver power readings and showing them would
# just clutter the picker.
SUPPORTED_ENERGY_MODELS = ('P110', 'P110M', 'P115', 'HS110', 'KP115', 'EP10')

LIFECYCLE_ACTIVE = 'active'
LIFECYCLE_EXCLUDED = 'excluded'
LIFECYCLE_ARCHIVED = 'archived'
VALID_LIFECYCLES = (LIFECYCLE_ACTIVE, LIFECYCLE_EXCLUDED, LIFECYCLE_ARCHIVED)

STATUS_ONLINE = 'online'
STATUS_OFFLINE = 'offline'
STATUS_MISSING = 'missing'
STATUS_UNKNOWN = 'unknown'


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def _atomic_write_json(path: Path, payload: Any) -> None:
    """Write JSON atomically: tmp file in the same dir, fsync, rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def empty_registry() -> Dict[str, Any]:
    return {
        'version': REGISTRY_VERSION,
        'last_refreshed_at': None,
        'last_refresh_summary': None,
        'devices': {},
    }


def load_registry(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return empty_registry()
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        if not isinstance(data, dict) or 'devices' not in data:
            return empty_registry()
        # Defensive: ensure required top-level keys exist
        data.setdefault('version', REGISTRY_VERSION)
        data.setdefault('last_refreshed_at', None)
        data.setdefault('last_refresh_summary', None)
        if not isinstance(data['devices'], dict):
            data['devices'] = {}
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"WARN: failed to read registry at {path}: {e}; starting fresh")
        return empty_registry()


def save_registry(path: Path, registry: Dict[str, Any]) -> None:
    _atomic_write_json(path, registry)


def excluded_aliases(registry: Dict[str, Any]) -> List[str]:
    """List of aliases the collector should skip on every poll cycle."""
    return [
        alias for alias, dev in registry.get('devices', {}).items()
        if dev.get('lifecycle') == LIFECYCLE_EXCLUDED
    ]


def excluded_device_ids(registry: Dict[str, Any]) -> List[str]:
    """Same as excluded_aliases but device_id (used by the collector to filter)."""
    return [
        dev['device_id']
        for dev in registry.get('devices', {}).values()
        if dev.get('lifecycle') == LIFECYCLE_EXCLUDED and dev.get('device_id')
    ]


def merge_api_response(
    registry: Dict[str, Any],
    api_devices: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """
    Merge a fresh `getDeviceList` response into the registry.

    `api_devices` is expected to be the raw list from TP-Link, each item with
    deviceId/alias/model/online keys. Unsupported models are dropped here.

    Returns (updated_registry, summary) where summary has counts of
    online/offline/missing/newly_discovered.
    """
    now = _now_iso()
    devices = registry.setdefault('devices', {})

    # Filter to supported models only
    filtered = [
        d for d in api_devices
        if (d.get('model') or '') in SUPPORTED_ENERGY_MODELS and d.get('alias')
    ]
    api_by_alias = {d['alias']: d for d in filtered}

    online_count = 0
    offline_count = 0
    newly_discovered = 0

    for alias, api_dev in api_by_alias.items():
        is_online = bool(api_dev.get('online'))
        new_status = STATUS_ONLINE if is_online else STATUS_OFFLINE
        if is_online:
            online_count += 1
        else:
            offline_count += 1

        if alias in devices:
            existing = devices[alias]
            existing['device_id'] = api_dev.get('deviceId') or existing.get('device_id')
            existing['model'] = api_dev.get('model') or existing.get('model')
            existing['status'] = new_status
            existing['status_checked_at'] = now
            existing['last_seen_in_api_at'] = now
            sources = existing.setdefault('source', [])
            if 'api' not in sources:
                sources.append('api')
        else:
            newly_discovered += 1
            devices[alias] = {
                'device_id': api_dev.get('deviceId'),
                'alias': alias,
                'model': api_dev.get('model'),
                'lifecycle': LIFECYCLE_ACTIVE,
                'lifecycle_changed_at': now,
                'lifecycle_reason': None,
                'status': new_status,
                'status_checked_at': now,
                'first_seen_at': now,
                'last_seen_in_api_at': now,
                'source': ['api'],
            }

    # Devices the registry knows about but the API didn't return
    missing_count = 0
    for alias, existing in devices.items():
        if alias in api_by_alias:
            continue
        # Operator-controlled lifecycles: don't touch status
        if existing.get('lifecycle') in (LIFECYCLE_EXCLUDED, LIFECYCLE_ARCHIVED):
            continue
        existing['status'] = STATUS_MISSING
        existing['status_checked_at'] = now
        missing_count += 1

    summary = {
        'online': online_count,
        'offline': offline_count,
        'missing': missing_count,
        'newly_discovered': newly_discovered,
    }
    registry['last_refreshed_at'] = now
    registry['last_refresh_summary'] = summary
    return registry, summary


def set_lifecycle(
    registry: Dict[str, Any],
    alias: str,
    lifecycle: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Mutate registry in place; raise ValueError on bad inputs."""
    if lifecycle not in VALID_LIFECYCLES:
        raise ValueError(f"Invalid lifecycle '{lifecycle}'; expected one of {VALID_LIFECYCLES}")
    devices = registry.get('devices', {})
    if alias not in devices:
        raise ValueError(f"Device '{alias}' not in registry")
    dev = devices[alias]
    dev['lifecycle'] = lifecycle
    dev['lifecycle_changed_at'] = _now_iso()
    dev['lifecycle_reason'] = reason
    return dev


_STATUS_SORT_PRIORITY = {
    STATUS_ONLINE: 0,
    STATUS_OFFLINE: 1,
    STATUS_MISSING: 2,
    STATUS_UNKNOWN: 3,
}


def _device_sort_key(dev: Dict[str, Any]):
    """Active devices: online first, then offline/missing/unknown, alphabetical within."""
    priority = _STATUS_SORT_PRIORITY.get(dev.get('status'), 99)
    return (priority, (dev.get('alias') or '').lower())


def view_for_template(registry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reshape the registry into something the Jinja template renders cleanly.

    Active devices are sorted online → offline → missing → unknown, alphabetical
    within each tier — matches what an operator scans the list for first.
    Excluded and archived sections stay alphabetical (their status is secondary).

    Returns:
        {
          'last_refreshed_at': ISO or None,
          'last_refresh_summary': {...} or None,
          'active':   [device, ...]  (status-priority, then alias),
          'excluded': [device, ...]  (alias),
          'archived': [device, ...]  (alias),
        }
    """
    active, excluded, archived = [], [], []
    for dev in registry.get('devices', {}).values():
        bucket = {
            LIFECYCLE_ACTIVE: active,
            LIFECYCLE_EXCLUDED: excluded,
            LIFECYCLE_ARCHIVED: archived,
        }.get(dev.get('lifecycle'), active)
        bucket.append(dev)

    active.sort(key=_device_sort_key)
    excluded.sort(key=lambda d: (d.get('alias') or '').lower())
    archived.sort(key=lambda d: (d.get('alias') or '').lower())

    return {
        'last_refreshed_at': registry.get('last_refreshed_at'),
        'last_refresh_summary': registry.get('last_refresh_summary'),
        'active': active,
        'excluded': excluded,
        'archived': archived,
    }


# ---------------------------------------------------------------------------
# Refresh request / result protocol — collector mediates all TP-Link calls.
# Admin writes a request; collector picks it up at the top of its sleep loop,
# calls getDeviceList, writes a result. Admin polls for the matching result.
# ---------------------------------------------------------------------------

def write_refresh_request(request_path: Path) -> str:
    """Write a fresh refresh request and return its request_id."""
    request_id = str(uuid.uuid4())
    payload = {
        'request_id': request_id,
        'requested_at': _now_iso(),
    }
    _atomic_write_json(request_path, payload)
    return request_id


def read_refresh_result(result_path: Path, request_id: str) -> Optional[Dict[str, Any]]:
    """Return the result payload IF it matches `request_id`, else None."""
    if not result_path.exists():
        return None
    try:
        with open(result_path, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get('request_id') != request_id:
        return None
    return data


def write_refresh_result(result_path: Path, payload: Dict[str, Any]) -> None:
    """Used by the collector. Writes result atomically."""
    _atomic_write_json(result_path, payload)


def clear_request_and_result(request_path: Path, result_path: Path) -> None:
    """Best-effort cleanup after admin has consumed a result."""
    for p in (request_path, result_path):
        try:
            if p.exists():
                p.unlink()
        except OSError:
            pass
