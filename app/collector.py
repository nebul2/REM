#!/usr/bin/env python3
import requests
import calendar
import time
import logging
import json
import os
import sys
import yaml
import psycopg2
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from psycopg2.extras import execute_values

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CONF_FILE = os.getenv("CONF_FILE", "/app/config/config.yaml")
# Same file the admin UI writes (see docker-compose: mount admin volume under /app/data/admin for collector)
COLLECTOR_CONTROL_FILE = os.getenv("COLLECTOR_CONTROL_FILE", "/app/data/collector_control.json")
# Runtime status for admin UI (same volume as control; collector must mount admin-data rw)
COLLECTOR_STATUS_FILE = os.getenv(
    "COLLECTOR_STATUS_FILE",
    os.path.join(os.path.dirname(COLLECTOR_CONTROL_FILE), "collector_status.json"),
)

# Device registry + refresh-fleet protocol (admin volume — same dir as the control file)
_ADMIN_DATA_DIR = os.path.dirname(COLLECTOR_CONTROL_FILE)
DEVICE_REGISTRY_FILE = os.path.join(_ADMIN_DATA_DIR, "device_registry.json")
REFRESH_FLEET_REQUEST_FILE = os.path.join(_ADMIN_DATA_DIR, "refresh_fleet_request.json")
REFRESH_FLEET_RESULT_FILE = os.path.join(_ADMIN_DATA_DIR, "refresh_fleet_result.json")

_logged_poll_interval = None

# Per-cycle TP-Link rate-limit / overload hits (threads update from parallel device polls)
_rate_lock = threading.Lock()
_rate_hits = 0


def reset_rate_limit_hits() -> None:
    global _rate_hits
    with _rate_lock:
        _rate_hits = 0


def note_rate_limit() -> None:
    global _rate_hits
    with _rate_lock:
        _rate_hits += 1


def get_rate_limit_hits() -> int:
    with _rate_lock:
        return _rate_hits


def _tplink_msg_suggests_rate_limit(resp_json: dict) -> bool:
    if not isinstance(resp_json, dict):
        return False
    msg = (
        str(
            resp_json.get("errMessage")
            or resp_json.get("message")
            or resp_json.get("msg")
            or ""
        )
    ).lower()
    if not msg:
        return False
    keywords = (
        "rate",
        "limit",
        "too many",
        "frequent",
        "overload",
        "throttl",
        "busy",
        "try again",
        "later",
        "quota",
        "exceed",
    )
    return any(k in msg for k in keywords)


def _tplink_is_rate_limited_http(status_code: int, resp_json: dict) -> bool:
    if status_code == 429:
        return True
    # 503 often means overload; 502 can be transient — opt-in via env
    if status_code == 503:
        return True
    if status_code == 502 and os.getenv("COLLECTOR_TPLINK_502_IS_OVERLOAD", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return True
    return _tplink_msg_suggests_rate_limit(resp_json)


def _apply_poll_interval_env(config: dict) -> None:
    """
    Docker Compose sets POLL_INTERVAL; config.yaml provides the default.
    Each device gets one reading per full poll cycle; cycle spacing = this interval (seconds).
    """
    raw = os.getenv("POLL_INTERVAL", "").strip()
    if not raw:
        return
    try:
        sec = int(raw)
    except ValueError:
        logger.warning("Ignoring invalid POLL_INTERVAL=%r", raw)
        return
    if sec < 5 or sec > 300:
        logger.warning("Ignoring POLL_INTERVAL=%s (valid range 5–300 seconds)", sec)
        return
    config.setdefault("poller", {})["interval"] = sec
    logger.info("Poll interval %ss from POLL_INTERVAL environment variable", sec)


def _poll_interval_seconds(config: dict) -> int:
    """
    Seconds between full poll cycles (one sample per device per cycle).

    Precedence:
    1. collector_control.json (written by admin UI — must share volume with collector; see docker-compose)
    2. config poller.interval (from POLL_INTERVAL env and/or config.yaml)
    """
    global _logged_poll_interval
    sec = None
    source = None
    try:
        if os.path.exists(COLLECTOR_CONTROL_FILE):
            with open(COLLECTOR_CONTROL_FILE, "r", encoding="utf-8") as f:
                control = json.load(f)
            pi = control.get("poll_interval")
            if pi is not None:
                v = int(pi)
                if 5 <= v <= 300:
                    sec = v
                    source = "collector_control.json (admin UI)"
    except (TypeError, ValueError, OSError, json.JSONDecodeError) as e:
        logger.warning("Could not read poll_interval from %s: %s", COLLECTOR_CONTROL_FILE, e)
    except Exception as e:
        logger.warning("Unexpected error reading %s: %s", COLLECTOR_CONTROL_FILE, e)

    if sec is None:
        sec = int(config["poller"]["interval"])
        source = "config / POLL_INTERVAL env"

    if sec != _logged_poll_interval:
        logger.info("Using poll interval %ss from %s", sec, source)
        _logged_poll_interval = sec
    return sec


#visit this in browser first to get the 'code'
# https://aps1-openapi.tplinknbu.com/v1/oauth/authorize?client_id=fdcae128-0adf-4233-8a58-30760652bd16&response_type=code&scope=all&state=123456789012345678901234&redirect_uri=https://www.greeningofstreaming.org

TOKEN_INVALID_ERROR_CODE = -10902


class TokenInvalidError(RuntimeError):
    """Raised when TP-Link access token is invalid/expired."""
    pass


class RateLimitError(RuntimeError):
    """Raised when TP-Link cloud signals rate limit or overload (e.g. getDeviceList)."""
    pass


def _control_defaults() -> dict:
    # Default to disabled: a fresh deploy should not hammer the TP-Link API
    # until an operator explicitly turns the collector on via the admin UI.
    return {
        "enabled": False,
        "poll_interval": 30,
        "device_query_delay": 0.5,
        "parallel_workers": 8,
        "adaptive_backoff": True,
        # Cap on devices an experiment can poll under focus_level=2 (Strong).
        # Bounds round time so a tight target_cadence_s (e.g. 10s) is achievable.
        # POLLING_ANALYSIS_MAY26.md sweep showed fleet sizes above ~12 in a
        # single chunk start hitting TP-Link's per-second burst behaviour.
        "experiment_max_devices": 12,
        # System-wide focus level. 0 = off (ambient polling for everyone at
        # poll_interval), 2 = strong (only the running experiment's devices
        # polled at its target_cadence_s, others paused). Level 1 (Mid —
        # interleaved cadences) is captured as CR-001 and not yet implemented.
        "focus_level": 0,
    }


# Paths to the experiment + group files (admin's volume); collector reads
# these at the top of each cycle in Focus Mode to discover the active focus.
EXPERIMENTS_FILE = os.path.join(_ADMIN_DATA_DIR, "experiments.json")
DEVICE_GROUPS_FILE = os.path.join(_ADMIN_DATA_DIR, "device_groups.json")
ANNOTATIONS_FILE = os.path.join(_ADMIN_DATA_DIR, "annotations.json")
# Written by the admin's field API (field_api.py): aliases currently being
# measured locally by LEM instances, with per-alias TTL expiry.
FIELD_SESSIONS_FILE = os.path.join(_ADMIN_DATA_DIR, "field_sessions.json")


def read_collector_control() -> dict:
    """Full control dict with defaults (for adaptive backoff)."""
    out = _control_defaults()
    try:
        if os.path.exists(COLLECTOR_CONTROL_FILE):
            with open(COLLECTOR_CONTROL_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                out.update(raw)
    except (OSError, json.JSONDecodeError, TypeError) as e:
        logger.warning("Could not read collector control: %s", e)
    return out


class AdaptiveBackoff:
    """
    Reduce load when TP-Link signals rate limit / overload; recover after clean cycles.

    Effective settings scale from configured UI values — does not rewrite collector_control.json.
    """

    def __init__(self, status_path: str):
        self.status_path = status_path
        self.level = 0
        self.success_streak = 0
        self.total_rate_events = 0
        self.last_cycle_rate_hits = 0
        self._load_state()

    def _load_state(self) -> None:
        try:
            if os.path.exists(self.status_path):
                with open(self.status_path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                st = d.get("adaptive_state") or {}
                self.level = max(0, min(8, int(st.get("backoff_level", 0))))
                self.success_streak = max(0, int(st.get("success_streak", 0)))
                self.total_rate_events = int(st.get("total_rate_events", 0))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

    def _success_streak_needed(self) -> int:
        try:
            return max(2, min(10, int(os.getenv("COLLECTOR_BACKOFF_RECOVER_STREAK", "3"))))
        except ValueError:
            return 3

    def effective(self, control: dict) -> dict:
        base_pi = int(control.get("poll_interval") or 30)
        base_pi = max(5, min(300, base_pi))
        base_w = _parse_parallel_workers(control)
        base_d = float(control.get("device_query_delay", 0.5))
        base_d = max(0.0, min(5.0, base_d))

        if not control.get("adaptive_backoff", True):
            return {
                "poll_interval": base_pi,
                "parallel_workers": base_w,
                "device_query_delay": base_d,
                "backoff_level": 0,
            }

        lv = self.level
        mult = 2 ** min(lv, 4)
        eff_pi = min(300, base_pi * mult)
        eff_w = max(1, base_w - (lv + 1) // 2)
        eff_d = min(5.0, base_d + 0.25 * lv)

        return {
            "poll_interval": eff_pi,
            "parallel_workers": eff_w,
            "device_query_delay": eff_d,
            "backoff_level": lv,
        }

    def reset(self) -> None:
        """Clear backoff (e.g. admin requested)."""
        self.level = 0
        self.success_streak = 0

    def record_cycle(self, rate_hits: int, cycle_completed: bool) -> None:
        self.last_cycle_rate_hits = rate_hits
        if rate_hits > 0:
            self.total_rate_events += rate_hits
            self.success_streak = 0
            self.level = min(8, self.level + 1)
            logger.warning(
                "TP-Link rate limit / overload: %s event(s) this cycle; "
                "adaptive backoff level now %s (calmer settings until recovery)",
                rate_hits,
                self.level,
            )
        elif cycle_completed:
            self.success_streak += 1
            need = self._success_streak_needed()
            if self.level > 0 and self.success_streak >= need:
                self.level = max(0, self.level - 1)
                self.success_streak = 0
                logger.info(
                    "Adaptive backoff: recovered one step (level now %s after %s clean cycles)",
                    self.level,
                    need,
                )

    def write_status_file(
        self,
        control: dict,
        eff: dict,
        *,
        rate_hits: int,
        cycle_completed: bool,
        last_error: str | None = None,
        focus_state: dict | None = None,
    ) -> None:
        try:
            ts_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            if rate_hits > 0:
                health = "throttled"
            elif self.level > 0:
                health = "recovering"
            else:
                health = "ok"

            payload = {
                "updated_at": ts_utc,
                "health": health,
                "adaptive_backoff_enabled": bool(control.get("adaptive_backoff", True)),
                "configured": {
                    "poll_interval": int(control.get("poll_interval") or 30),
                    "parallel_workers": _parse_parallel_workers(control),
                    "device_query_delay": float(control.get("device_query_delay", 0.5)),
                },
                "effective": {
                    "poll_interval": eff["poll_interval"],
                    "parallel_workers": eff["parallel_workers"],
                    "device_query_delay": eff["device_query_delay"],
                    "backoff_level": eff.get("backoff_level", 0),
                },
                "adaptive_state": {
                    "backoff_level": self.level,
                    "success_streak": self.success_streak,
                    "total_rate_events": self.total_rate_events,
                    "rate_limit_hits_last_cycle": rate_hits,
                },
                "last_cycle_ok": cycle_completed,
                "last_error": last_error or "",
                "focus": focus_state or {"active": False},
            }
            d = os.path.dirname(self.status_path)
            if d:
                os.makedirs(d, exist_ok=True)
            tmp = self.status_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp, self.status_path)
        except OSError as e:
            logger.warning("Could not write collector status file %s: %s", self.status_path, e)


def getToken():
    # Load refresh token, preferring the persisted token file.
    # TP-Link rotates refresh tokens, so persisted token is usually newest.
    refreshToken = ""
    token_file = os.getenv("TOKEN_FILE", "/app/data/refresh_token.txt")
    if os.path.exists(token_file):
        try:
            with open(token_file, "r") as f:
                refreshToken = f.readline().strip()
        except Exception as e:
            logger.warning(f"Could not read refresh token from {token_file}: {e}")

    if not refreshToken:
        refreshToken = os.getenv("TPLINK_REFRESH_TOKEN", "")

    if len(refreshToken) >= 2:  # use refresh token to get access token
        authurl = 'https://aps1-openapi.tplinknbu.com/v1/oauth/token'
        getTokendata = {'client_id': 'fdcae128-0adf-4233-8a58-30760652bd16', 'grant_type': 'refresh_token', 'client_secret': '4087d4b9-5e0c-4e50-b06c-22580fc618d5', 'refresh_token': refreshToken}
        try:
            tokenResponse = requests.post(authurl, data=getTokendata, timeout=15)
            tokensjson = tokenResponse.json()
        except Exception as e:
            logger.error(f"Token refresh request failed: {e}")
            raise
        if tokensjson.get('errorCode') or tokensjson.get('error'):
            logger.error(f"Token refresh API error: {tokensjson}")
            raise RuntimeError(f"TP-Link token refresh failed: {tokensjson}")
        accessToken = tokensjson["accessToken"]
        refreshToken = tokensjson["refreshToken"]

    else:  # no refresh token: ask user for authorization code
        inputcode=input("Paste Code:")
        authurl='https://aps1-openapi.tplinknbu.com/v1/oauth/token'
        getTokendata = {'client_id': 'fdcae128-0adf-4233-8a58-30760652bd16', 'grant_type': 'code', 'client_secret': '4087d4b9-5e0c-4e50-b06c-22580fc618d5', 'code': inputcode}
        tokenResponse = requests.post(authurl, data=getTokendata)
        tokensjson = tokenResponse.json()
        accessToken=tokensjson["accessToken"]
        refreshToken=tokensjson["refreshToken"]

    # Save new refresh token to file for persistence
    try:
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        with open(token_file, "w") as f:
            f.write(refreshToken)
    except Exception as e:
        print(f"Warning: Could not save refresh token to {token_file}: {e}")

    return accessToken

# TP-Link models that support real-time energy (getDeviceRealTimeEnergy). Add others as needed.
SUPPORTED_ENERGY_MODELS = ('P110', 'P110M', 'P115', 'HS110', 'KP115', 'EP10')

def getDeviceIdList(accessToken):
    devListurl = 'https://aps1-openapi.tplinknbu.com/v1/getDeviceList?'
    getDevlistdata = {'client_id': 'fdcae128-0adf-4233-8a58-30760652bd16', 'api_key': 'e71bf02f-8b71-42ee-8af0-62a7bdf6c866', 'token': accessToken}
    try:
        devList = requests.post(devListurl, data=getDevlistdata, timeout=15)
    except Exception as e:
        logger.error(f"TP-Link getDeviceList request failed: {e}")
        return []

    try:
        resp = devList.json()
    except Exception:
        resp = {}

    if not isinstance(resp, dict):
        resp = {}

    if _tplink_is_rate_limited_http(devList.status_code, resp):
        raise RateLimitError(
            f"TP-Link getDeviceList rate limited or overloaded: HTTP {devList.status_code} {resp}"
        )

    if resp.get('errorCode') == TOKEN_INVALID_ERROR_CODE or str(resp.get("errMessage", "")).lower() == "token invalid":
        raise TokenInvalidError(f"TP-Link token invalid: {resp}")

    if resp.get('errorCode') or resp.get('error'):
        if _tplink_msg_suggests_rate_limit(resp):
            raise RateLimitError(f"TP-Link getDeviceList rate limited: {resp}")
        logger.error(f"TP-Link getDeviceList API error: {resp}")
        return []

    devices = resp.get("devices")
    if devices is None:
        logger.warning("TP-Link getDeviceList response has no 'devices' key: %s", resp)
        return []

    deviceIdList = []
    skipped_offline = 0
    skipped_model = 0
    for item in devices:
        if item.get('online') is False:
            skipped_offline += 1
            continue
        model = item.get('model') or ''
        if model not in SUPPORTED_ENERGY_MODELS:
            skipped_model += 1
            continue
        deviceIdList.append({'deviceId': item['deviceId'], 'alias': item.get('alias') or item['deviceId']})

    logger.info("TP-Link devices: %d from API, %d used (skipped %d offline, %d unsupported model)",
                len(devices), len(deviceIdList), skipped_offline, skipped_model)
    if deviceIdList:
        logger.info("Collecting from: %s", [d['alias'] for d in deviceIdList])
    return deviceIdList


def _parse_parallel_workers(control: dict) -> int:
    """Concurrent device API calls per chunk (1 = legacy sequential). Env overrides if set."""
    raw_env = os.getenv("COLLECTOR_PARALLEL_WORKERS", "").strip()
    if raw_env:
        try:
            n = int(raw_env)
        except ValueError:
            n = 8
    else:
        try:
            n = int(control.get("parallel_workers", 8))
        except (TypeError, ValueError):
            n = 8
    return max(1, min(32, n))


def _chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def getDevPower(deviceId, accessToken):
    """Get power reading from a device. Returns None on failure."""
    try:
        devPowerurl='https://aps1-openapi.tplinknbu.com/v1/device/deviceControl?client_id=fdcae128-0adf-4233-8a58-30760652bd16&api_key=e71bf02f-8b71-42ee-8af0-62a7bdf6c866&token=' + accessToken
        getDevpowerlistdata={"method": "getDeviceRealTimeEnergy", "device": {"id": deviceId }}
        session = requests.Session()
        session.headers.update({'Content-Type': 'application/json'})

        devPowerlist = session.post(devPowerurl, json=getDevpowerlistdata, timeout=10)

        try:
            response_json = devPowerlist.json()
        except Exception:
            response_json = {}

        if not isinstance(response_json, dict):
            response_json = {}

        if _tplink_is_rate_limited_http(devPowerlist.status_code, response_json):
            note_rate_limit()
            logger.warning(
                "TP-Link rate limit/overload on device %s: HTTP %s %s",
                deviceId,
                devPowerlist.status_code,
                response_json,
            )
            return None

        if devPowerlist.status_code >= 400:
            devPowerlist.raise_for_status()

        if _tplink_msg_suggests_rate_limit(response_json):
            note_rate_limit()
            logger.warning(
                "TP-Link rate-limit style message for device %s: %s",
                deviceId,
                response_json,
            )
            return None

        # Check if response has expected structure
        if 'result' not in response_json or 'powerWatts' not in response_json.get('result', {}):
            logger.warning(f"Unexpected API response structure for device {deviceId}: {response_json}")
            return None

        power_watts = response_json['result']['powerWatts']

        try:
            power_float = float(power_watts)
            if power_float < 0:
                logger.warning(f"Invalid power reading for device {deviceId}: {power_float}W (negative)")
                return None
            return power_float
        except (ValueError, TypeError):
            logger.warning(f"Non-numeric power reading for device {deviceId}: {power_watts}")
            return None

    except requests.exceptions.Timeout:
        logger.error(f"Timeout reading device {deviceId} (API took >10s)")
        return None
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 429:
            note_rate_limit()
            logger.warning("HTTP 429 for device %s", deviceId)
            return None
        logger.error(f"HTTP error reading device {deviceId}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error reading device {deviceId}: {e}")
        return None
    except KeyError as e:
        logger.error(f"Missing key in API response for device {deviceId}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error reading device {deviceId}: {e}", exc_info=True)
        return None


def _poll_one_device(item, accessToken):
    """Worker: return (alias, power or None)."""
    power = getDevPower(item["deviceId"], accessToken)
    return item["alias"], power


def collect_power_readings(deviceIdList, accessToken, parallel_workers, device_query_delay):
    """
    Poll all devices (sequential or parallel chunks) and return points + failures.
    Used by getDevicePowerList and benchmark_poll_cycle.
    """
    points_buffer = []
    failed_devices = []
    device_query_delay = float(device_query_delay)

    if parallel_workers <= 1:
        for item in deviceIdList:
            device_id = item["deviceId"]
            alias = item["alias"]
            devPower = getDevPower(device_id, accessToken)
            if devPower is None:
                failed_devices.append(alias)
                if device_query_delay > 0:
                    time.sleep(device_query_delay)
                continue
            timestamp = time.time()  # float, sub-second precision (was integer-truncated)
            points_buffer.append(
                {"alias": alias, "power_watts": float(devPower), "time": timestamp}
            )
            if device_query_delay > 0:
                time.sleep(device_query_delay)
    else:
        chunks = list(_chunked(deviceIdList, parallel_workers))
        for ci, chunk in enumerate(chunks):
            with ThreadPoolExecutor(max_workers=len(chunk)) as pool:
                futures = [
                    pool.submit(_poll_one_device, item, accessToken) for item in chunk
                ]
                for fut in as_completed(futures):
                    alias, devPower = fut.result()
                    if devPower is None:
                        failed_devices.append(alias)
                        continue
                    timestamp = time.time()  # float, sub-second precision
                    points_buffer.append(
                        {
                            "alias": alias,
                            "power_watts": float(devPower),
                            "time": timestamp,
                        }
                    )
            if device_query_delay > 0 and ci < len(chunks) - 1:
                time.sleep(device_query_delay)

    return points_buffer, failed_devices


def getDevicePowerList(
    deviceIdList,
    accessToken,
    config,
    db_conn,
    parallel_workers_override=None,
    device_query_delay_override=None,
):
    """Poll all devices and write valid readings to database. Skips failed devices."""
    devicePowerList = []

    control = {}
    device_query_delay = 0.5  # Default; between chunks when parallel, or between devices when sequential
    try:
        if os.path.exists(COLLECTOR_CONTROL_FILE):
            with open(COLLECTOR_CONTROL_FILE, "r", encoding="utf-8") as f:
                control = json.load(f)
                device_query_delay = float(control.get("device_query_delay", 0.5))
    except Exception as e:
        logger.warning(
            "Could not read collector control from %s: %s", COLLECTOR_CONTROL_FILE, e
        )

    if device_query_delay_override is not None:
        device_query_delay = float(device_query_delay_override)
    if parallel_workers_override is not None:
        parallel_workers = max(1, min(32, int(parallel_workers_override)))
    else:
        parallel_workers = _parse_parallel_workers(control)
    chunks = list(_chunked(deviceIdList, parallel_workers)) if parallel_workers > 1 else []

    points_buffer, failed_devices = collect_power_readings(
        deviceIdList, accessToken, parallel_workers, device_query_delay
    )

    if parallel_workers > 1:
        logger.info(
            "Parallel device polling: up to %d workers per chunk, %d chunk(s), inter-chunk delay %ss (effective)",
            parallel_workers,
            len(chunks),
            device_query_delay,
        )
    
    # Log summary of polling results
    successful_count = len(points_buffer)
    total_count = len(deviceIdList)
    
    if failed_devices:
        logger.warning(f"Failed to read {len(failed_devices)} device(s): {', '.join(failed_devices)}")
    
    logger.info(f"Successfully read {successful_count}/{total_count} devices")
    
    # Batch insert all valid points to TimescaleDB
    if len(points_buffer) > 0:
        res = sendToTimescaleDB(db_conn, points_buffer)
        if not res:
            logger.error(f"Failed to send {len(points_buffer)} points to TimescaleDB")
        else:
            logger.info(f"Wrote {len(points_buffer)} points to TimescaleDB")
    
    return devicePowerList


def load_config():
    ''' Read the config file
    '''
    with open(CONF_FILE) as file:
        try:
            config = yaml.safe_load(file)
        except yaml.YAMLError as e:
            print(e)
            config = False

    return config


def _load_focus_state(control: dict):
    """
    Resolve the system-wide focus state for this cycle. Returns:
        (experiment_id, target_cadence_s, set_of_device_aliases)
    when system focus_level=2 AND a current experiment exists,
    otherwise (None, None, None) — collector falls back to ambient.

    System focus_level lives in collector_control.json (not per-experiment),
    so an operator can flip Off↔Strong from /exploration without editing the
    running experiment. The experiment still carries its preferred
    target_cadence_s (the cadence the operator wants when focus is on).

    Devices in the registry's excluded/archived lifecycle are filtered out
    here too (matches ambient mode behaviour — operator-paused devices are
    paused everywhere).
    """
    focus_level = 0
    try:
        focus_level = int(control.get('focus_level', 0) or 0)
    except (TypeError, ValueError):
        focus_level = 0
    # Level 1 (Mid) is deferred to CR-001 — for now treat anything other than
    # 2 as "off" so the collector behaves identically to before this knob landed.
    if focus_level != 2:
        return None, None, None

    try:
        if not os.path.exists(EXPERIMENTS_FILE):
            return None, None, None
        with open(EXPERIMENTS_FILE, 'r', encoding='utf-8') as f:
            experiments = json.load(f) or {}
        if not isinstance(experiments, dict):
            return None, None, None

        focus_exp_id = None
        focus_exp = None
        for exp_id, exp in experiments.items():
            if not isinstance(exp, dict):
                continue
            if exp.get('is_current'):
                focus_exp_id = exp_id
                focus_exp = exp
                break
        if not focus_exp:
            return None, None, None

        target_cadence_s = int(focus_exp.get('target_cadence_s') or 10)
        if target_cadence_s < 5 or target_cadence_s > 300:
            target_cadence_s = 10

        # Resolve linked_groups → aliases
        groups = {}
        if os.path.exists(DEVICE_GROUPS_FILE):
            try:
                with open(DEVICE_GROUPS_FILE, 'r', encoding='utf-8') as f:
                    groups = json.load(f) or {}
            except (OSError, json.JSONDecodeError):
                pass
        aliases = set()
        for group_name in (focus_exp.get('linked_groups') or []):
            g = groups.get(group_name)
            if isinstance(g, dict):
                for alias in (g.get('devices') or []):
                    if alias:
                        aliases.add(alias)

        # Drop excluded/archived (operator wins everywhere)
        excluded_aliases, _excluded_ids = _load_excluded_keys()
        if excluded_aliases:
            aliases -= excluded_aliases

        return focus_exp_id, target_cadence_s, aliases
    except Exception as e:
        logger.warning("Could not resolve focus state: %s", e)
        return None, None, None


def _filter_to_focus(deviceIdList, focus_aliases):
    """In Focus Mode keep ONLY devices whose alias is in the focus set."""
    return [d for d in deviceIdList if d.get('alias') in focus_aliases]


def _append_annotation(experiment_id: str, label: str, description: str = "") -> None:
    """Append an annotation to annotations.json. Best-effort — never raises."""
    try:
        annotations = {}
        if os.path.exists(ANNOTATIONS_FILE):
            try:
                with open(ANNOTATIONS_FILE, 'r', encoding='utf-8') as f:
                    annotations = json.load(f) or {}
            except (OSError, json.JSONDecodeError):
                annotations = {}
        if not isinstance(annotations, dict):
            annotations = {}

        ann_id = f"focus-{int(time.time() * 1000)}"
        annotations[ann_id] = {
            'id': ann_id,
            'experiment_id': experiment_id,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'label': label,
            'description': description,
            'color': '#2d6a4f',
            'auto_generated': True,
        }
        tmp = ANNOTATIONS_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(annotations, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, ANNOTATIONS_FILE)
    except Exception as e:
        logger.warning("Could not write focus annotation: %s", e)


def _compute_health(round_s: float, tick_s: float) -> str:
    """% of tick used by last round → green/yellow/orange/red label."""
    if tick_s <= 0:
        return 'unknown'
    pct = round_s / tick_s
    if pct <= 0.30:
        return 'green'
    if pct <= 0.70:
        return 'yellow'
    if pct <= 0.95:
        return 'orange'
    return 'red'


def _load_excluded_keys():
    """
    Read the admin-side device registry and return (excluded_aliases, excluded_device_ids).

    Devices with lifecycle in {excluded, archived} are skipped on every poll cycle —
    this is the operator's "stop polling this device" signal (see admin UI /manage).
    Returns empty sets if the registry is missing or malformed; logs at WARNING.
    """
    try:
        if not os.path.exists(DEVICE_REGISTRY_FILE):
            return set(), set()
        with open(DEVICE_REGISTRY_FILE, "r", encoding="utf-8") as f:
            registry = json.load(f)
        devices = registry.get("devices", {}) if isinstance(registry, dict) else {}
        aliases, device_ids = set(), set()
        for alias, dev in devices.items():
            if not isinstance(dev, dict):
                continue
            if dev.get("lifecycle") in ("excluded", "archived"):
                aliases.add(alias)
                if dev.get("device_id"):
                    device_ids.add(dev["device_id"])
        return aliases, device_ids
    except (OSError, json.JSONDecodeError, TypeError) as e:
        logger.warning("Could not read device registry %s: %s", DEVICE_REGISTRY_FILE, e)
        return set(), set()


def _filter_excluded(deviceIdList, excluded_aliases, excluded_device_ids):
    """Return (kept_devices, skipped_count) honouring registry lifecycle."""
    if not excluded_aliases and not excluded_device_ids:
        return deviceIdList, 0
    kept = []
    skipped = 0
    for d in deviceIdList:
        if d.get("alias") in excluded_aliases or d.get("deviceId") in excluded_device_ids:
            skipped += 1
            continue
        kept.append(d)
    return kept, skipped


def _load_field_covered_aliases():
    """Aliases currently covered by a local LEM measurement session (unexpired
    TTL in field_sessions.json). Fail open — any error means we keep cloud
    polling, since data continuity beats API savings."""
    try:
        if not os.path.exists(FIELD_SESSIONS_FILE):
            return set()
        with open(FIELD_SESSIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        now = datetime.now(timezone.utc)
        covered = set()
        for alias, info in (data.get("aliases") or {}).items():
            try:
                if datetime.fromisoformat(info["expires_at"]) > now:
                    covered.add(alias)
            except Exception:
                continue
        return covered
    except Exception:
        return set()


def _atomic_write_json(path, payload):
    """Atomic JSON write — tmp file in the same dir, rename. Mirrors admin/device_registry.py."""
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def _read_pending_refresh_request():
    """Return the pending request payload (with request_id) or None."""
    if not os.path.exists(REFRESH_FLEET_REQUEST_FILE):
        return None
    try:
        with open(REFRESH_FLEET_REQUEST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("request_id"):
            return data
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Bad refresh request file: %s", e)
    return None


def _raw_get_device_list(accessToken):
    """
    Like getDeviceIdList but returns the raw API list (deviceId/alias/model/online)
    without filtering by online/model — the registry needs the full picture so the
    admin UI can show offline-but-known devices and excluded-by-operator devices.
    """
    devListurl = 'https://aps1-openapi.tplinknbu.com/v1/getDeviceList?'
    getDevlistdata = {
        'client_id': 'fdcae128-0adf-4233-8a58-30760652bd16',
        'api_key': 'e71bf02f-8b71-42ee-8af0-62a7bdf6c866',
        'token': accessToken,
    }
    devList = requests.post(devListurl, data=getDevlistdata, timeout=15)
    try:
        resp = devList.json()
    except Exception:
        resp = {}
    if not isinstance(resp, dict):
        resp = {}

    if _tplink_is_rate_limited_http(devList.status_code, resp):
        raise RateLimitError(f"TP-Link getDeviceList rate limited: HTTP {devList.status_code} {resp}")
    if resp.get('errorCode') == TOKEN_INVALID_ERROR_CODE or str(resp.get("errMessage", "")).lower() == "token invalid":
        raise TokenInvalidError(f"TP-Link token invalid: {resp}")
    if resp.get('errorCode') or resp.get('error'):
        if _tplink_msg_suggests_rate_limit(resp):
            raise RateLimitError(f"TP-Link getDeviceList rate limited: {resp}")
        raise RuntimeError(f"TP-Link getDeviceList API error: {resp}")

    devices = resp.get("devices") or []
    out = []
    for item in devices:
        out.append({
            "deviceId": item.get("deviceId"),
            "alias": item.get("alias") or item.get("deviceId"),
            "model": item.get("model") or "",
            "online": bool(item.get("online")),
        })
    return out


def handle_refresh_fleet_request(accessToken):
    """
    If the admin has dropped a refresh request file, call getDeviceList and write
    the matching result. Token-invalid is propagated so the caller can refresh and
    retry on the next iteration. Returns True if a request was processed.
    """
    pending = _read_pending_refresh_request()
    if not pending:
        return False
    request_id = pending["request_id"]
    logger.info("Processing refresh-fleet request %s", request_id)

    try:
        api_devices = _raw_get_device_list(accessToken)
        result_payload = {
            "request_id": request_id,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ok": True,
            "error": None,
            "devices": api_devices,
        }
    except TokenInvalidError:
        # Re-raise so the main loop can refresh and retry on the next iteration
        raise
    except (RateLimitError, RuntimeError, requests.RequestException) as e:
        logger.error("Refresh-fleet request %s failed: %s", request_id, e)
        result_payload = {
            "request_id": request_id,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ok": False,
            "error": str(e),
            "devices": [],
        }

    try:
        _atomic_write_json(REFRESH_FLEET_RESULT_FILE, result_payload)
    except OSError as e:
        logger.error("Could not write refresh-fleet result: %s", e)
        return True
    # Best-effort: remove the request file so we don't reprocess
    try:
        os.unlink(REFRESH_FLEET_REQUEST_FILE)
    except OSError:
        pass
    return True


def pollCloud(config, db_conn, accessToken, eff, focus_aliases=None):
    """
    eff: dict from AdaptiveBackoff.effective() with parallel_workers and device_query_delay.

    focus_aliases: if not None, restrict polling to ONLY these device aliases
    (Focus Mode). Skips devices not in this set even if they're online and
    in the registry as active. The list call still happens (we need fresh
    device IDs for the focus aliases).
    """
    reset_rate_limit_hits()
    try:
        deviceIdList = getDeviceIdList(accessToken)
    except RateLimitError as e:
        logger.warning("%s", e)
        note_rate_limit()
        return

    if not deviceIdList:
        logger.warning("No TP-Link devices to poll (empty list)")
        return

    if focus_aliases is not None:
        before = len(deviceIdList)
        deviceIdList = _filter_to_focus(deviceIdList, focus_aliases)
        logger.info("Focus Mode: %d/%d devices selected for this cycle", len(deviceIdList), before)
        if not deviceIdList:
            logger.warning("Focus Mode: none of the experiment's devices are currently online — skipping cycle")
            return

    excluded_aliases, excluded_device_ids = _load_excluded_keys()
    deviceIdList, skipped = _filter_excluded(deviceIdList, excluded_aliases, excluded_device_ids)
    if skipped:
        logger.info("Skipping %d device(s) marked excluded/archived in registry", skipped)
    if not deviceIdList:
        logger.warning("All devices excluded by registry; nothing to poll this cycle")
        return

    covered = _load_field_covered_aliases()
    if covered:
        before = len(deviceIdList)
        deviceIdList = [d for d in deviceIdList if d.get("alias") not in covered]
        if before - len(deviceIdList):
            logger.info(
                "Skipping %d device(s) covered by a local LEM measurement session",
                before - len(deviceIdList),
            )
        if not deviceIdList:
            logger.info("All remaining devices covered by LEM; nothing to cloud-poll this cycle")
            return

    getDevicePowerList(
        deviceIdList,
        accessToken,
        config,
        db_conn,
        parallel_workers_override=eff.get("parallel_workers"),
        device_query_delay_override=eff.get("device_query_delay"),
    )


def do_work(config, db_conn, accessToken, eff, focus_aliases=None):
    """Execute one collection cycle. Returns True on success, False on failure."""
    try:
        pollCloud(config, db_conn, accessToken, eff, focus_aliases=focus_aliases)
        return True
    except TokenInvalidError:
        # Allow caller to refresh token and retry
        raise
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in do_work: {e}", exc_info=True)
        return False


def sendToTimescaleDB(db_conn, points_buffer):
    ''' Take a set of values, and send them to TimescaleDB
    '''
    try:
        # Check if connection is still alive
        try:
            cursor = db_conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            logger.error("Database connection is dead, cannot write data")
            return False
        
        cursor = db_conn.cursor()
        
        # Prepare data for batch insert. point['time'] is a float (sub-second
        # precision). Format with microseconds so the DB row reflects the actual
        # sample time rather than a truncated integer second — matters for
        # tick-aligned content where a 10s cadence must look like 10s in the
        # data, not 9–11s due to second-boundary rounding.
        values = []
        for point in points_buffer:
            dt = datetime.fromtimestamp(point['time'], tz=timezone.utc)
            ts = dt.strftime('%Y-%m-%d %H:%M:%S.%f+00')
            values.append((ts, point['alias'], point['power_watts']))
        
        # Batch insert using execute_values for efficiency
        execute_values(
            cursor,
            "INSERT INTO gos_rem (time, alias, power_watts) VALUES %s",
            values
        )
        
        db_conn.commit()
        cursor.close()
        return True
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
        logger.error(f"Database connection error writing to TimescaleDB: {e}")
        try:
            db_conn.rollback()
        except:
            pass
        return False
    except Exception as e:
        logger.error(f"Failed to write to TimescaleDB: {e}", exc_info=True)
        try:
            db_conn.rollback()
        except:
            pass
        return False


def get_db_connection(config):
    ''' Create PostgreSQL/TimescaleDB connection with retry logic
    '''
    # Read connection parameters from environment variables or config
    host = os.getenv("POSTGRES_HOST", config.get("postgresql", {}).get("host", "timescaledb"))
    port = os.getenv("POSTGRES_PORT", config.get("postgresql", {}).get("port", "5432"))
    database = os.getenv("POSTGRES_DB", config.get("postgresql", {}).get("database", "gos_rem"))
    user = os.getenv("POSTGRES_USER", config.get("postgresql", {}).get("user", "gos"))
    password = os.getenv("POSTGRES_PASSWORD", config.get("postgresql", {}).get("password", ""))
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                connect_timeout=10
            )
            # Test the connection
            test_cursor = conn.cursor()
            test_cursor.execute("SELECT 1")
            test_cursor.close()
            logger.info(f"Successfully connected to TimescaleDB (attempt {attempt + 1})")
            return conn
        except psycopg2.OperationalError as e:
            logger.warning(f"Database connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to TimescaleDB after {max_retries} attempts")
        except Exception as e:
            logger.error(f"Unexpected error connecting to database: {e}")
            return None
    
    return None


def _record_admin_error_collector_side(source: str, message: str, severity: str = "error") -> None:
    """
    Append an entry to the admin error log so it surfaces in the /exploration banner.
    Same file shape as admin/app.py:_record_admin_error. Best-effort; never raises.
    """
    try:
        admin_errors_file = os.path.join(_ADMIN_DATA_DIR, "admin_errors.json")
        entries = []
        if os.path.exists(admin_errors_file):
            try:
                with open(admin_errors_file, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                if isinstance(raw, list):
                    entries = raw
            except Exception:
                pass
        import uuid as _uuid
        entries.append({
            'id': str(_uuid.uuid4()),
            'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'source': source,
            'severity': severity,
            'message': message,
        })
        entries = entries[-25:]
        os.makedirs(_ADMIN_DATA_DIR, exist_ok=True)
        tmp = admin_errors_file + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, admin_errors_file)
    except Exception:
        pass


def _try_handle_refresh(accessToken):
    """Wrap handle_refresh_fleet_request; swallow TokenInvalidError (next cycle retries)."""
    try:
        return handle_refresh_fleet_request(accessToken)
    except TokenInvalidError:
        logger.info("Refresh-fleet hit token invalid; will retry on next cycle after token refresh")
        return False
    except Exception as e:
        logger.error("Refresh-fleet handler crashed: %s", e, exc_info=True)
        return False


def _sleep_until_with_refresh_check(deadline_monotonic, accessToken, refresh_chunk=2.0):
    """
    Sleep until `deadline_monotonic` (a value from time.monotonic()).

    Strategy: while there's plenty of time left (> 2 × refresh_chunk), do
    short chunked sleeps interleaved with refresh-fleet checks so the admin
    button responds quickly. For the FINAL 0–4 seconds, do a single
    sleep_until_deadline so wake-up precision is bounded by the OS's
    minimum sleep granularity (≲10 ms on Linux) rather than the cumulative
    overshoot of many chunks (≈50 ms per chunk).

    This matters for Focus Mode where the next-tick anchor must hit close
    to its target — every ms of wake-up jitter shows up as cadence variance
    in the DB.
    """
    while True:
        now = time.monotonic()
        remaining = deadline_monotonic - now
        if remaining <= 0:
            return
        if remaining > refresh_chunk * 2:
            time.sleep(refresh_chunk)
            _try_handle_refresh(accessToken)
        else:
            # Final segment — one precise sleep to the deadline.
            time.sleep(max(0.0, deadline_monotonic - time.monotonic()))
            return


def _sleep_with_refresh_check(total_seconds, accessToken, chunk=2.0):
    """
    Sleep for `total_seconds`, but check for refresh-fleet requests every `chunk` seconds
    so the admin button doesn't have to wait a full poll interval.

    Thin wrapper around _sleep_until_with_refresh_check — converts a
    duration into an absolute monotonic deadline.
    """
    deadline = time.monotonic() + max(0.0, float(total_seconds))
    _sleep_until_with_refresh_check(deadline, accessToken, refresh_chunk=chunk)


def main():
    accessToken = getToken()

    config = load_config()
    if not config:
       sys.exit(1)

    _apply_poll_interval_env(config)

    # Create the PostgreSQL/TimescaleDB connection
    db_conn = get_db_connection(config)
    if not db_conn:
        print("Failed to connect to database")
        sys.exit(1)

    # Should we be running an infinite loop?
    persist = False
    if "poller" in config and "persist" in config['poller']:
        if "interval" not in config["poller"]:
            print("Err: Persistent mode enabled, but interval not defined")
        else:
            persist = True

    if not persist:
        # Trigger the poller as a one-shot thing (no adaptive backoff file)
        eff_once = {
            "parallel_workers": None,
            "device_query_delay": None,
        }
        try:
            do_work(config, db_conn, accessToken, eff_once)
        except TokenInvalidError:
            logger.warning("TP-Link token invalid in one-shot mode, refreshing token and retrying once")
            accessToken = getToken()
            do_work(config, db_conn, accessToken, eff_once)
        db_conn.close()
        return

    # Otherwise, set up a loop and poll periodically
    consecutive_failures = 0
    max_consecutive_failures = 10  # Exit after 10 consecutive failures
    backoff = AdaptiveBackoff(COLLECTOR_STATUS_FILE)
    last_eff = None
    last_err = ""
    reset_touch = os.path.join(
        os.path.dirname(COLLECTOR_CONTROL_FILE), "reset_backoff"
    )

    # Focus Mode tick scheduling — see POLLING_ANALYSIS_MAY26.md §9.
    # `next_tick` is monotonic-clock anchored. Each tick we compute the
    # remaining slack; if round time exceeds the tick we record a slip.
    next_tick = None
    last_focus_id = None  # for boundary annotations

    try:
        while True:
            try:
                control = read_collector_control()
                if os.path.exists(reset_touch):
                    try:
                        os.unlink(reset_touch)
                    except OSError:
                        pass
                    backoff.reset()
                    logger.info("Adaptive backoff reset (operator requested via admin UI)")

                last_eff = backoff.effective(control)

                # Process refresh-fleet requests independently of the `enabled` toggle —
                # discovery doesn't write to the DB, and operators may want to populate
                # the registry on a freshly-deployed (idle) collector.
                _try_handle_refresh(accessToken)

                # Resolve focus state for this cycle. System focus_level lives in
                # control; combined with a running experiment it produces an
                # alias set. Off level (or no running experiment) returns None.
                focus_id, focus_tick_s, focus_aliases = _load_focus_state(control)
                in_focus = focus_id is not None and focus_aliases is not None

                # Boundary annotations on focus enter/exit — best-effort, never raises.
                if in_focus and last_focus_id != focus_id:
                    _append_annotation(focus_id, "Focus Mode started",
                                       f"Polling {len(focus_aliases)} device(s) at {focus_tick_s}s tick")
                    last_focus_id = focus_id
                elif not in_focus and last_focus_id is not None:
                    _append_annotation(last_focus_id, "Focus Mode ended", "")
                    last_focus_id = None

                # Honor the admin-UI / collector_control.json `enabled` toggle —
                # if disabled, sleep this cycle without touching TP-Link or the DB.
                if not control.get("enabled", False):
                    logger.info("Collector disabled (enabled=false in collector_control.json); skipping cycle")
                    _sleep_with_refresh_check(last_eff["poll_interval"], accessToken)
                    next_tick = None  # Reset tick scheduling when paused
                    continue

                # Check if database connection is still alive, reconnect if needed
                try:
                    test_cursor = db_conn.cursor()
                    test_cursor.execute("SELECT 1")
                    test_cursor.close()
                except (psycopg2.OperationalError, psycopg2.InterfaceError, AttributeError) as e:
                    logger.warning(f"Database connection lost ({type(e).__name__}), attempting to reconnect...")
                    try:
                        db_conn.close()
                    except:
                        pass
                    db_conn = get_db_connection(config)
                    if not db_conn:
                        logger.error("Failed to reconnect to database")
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            logger.error(f"Too many consecutive failures ({consecutive_failures}), exiting")
                            sys.exit(1)
                        sleep_s = (
                            last_eff["poll_interval"]
                            if last_eff
                            else _poll_interval_seconds(config)
                        )
                        _sleep_with_refresh_check(sleep_s, accessToken)
                        continue
                    logger.info("Successfully reconnected to database")

                last_err = ""
                round_t0 = time.monotonic()
                try:
                    success = do_work(config, db_conn, accessToken, last_eff,
                                      focus_aliases=focus_aliases if in_focus else None)
                except TokenInvalidError:
                    logger.warning("TP-Link token invalid, refreshing access token and retrying cycle")
                    try:
                        accessToken = getToken()
                        success = do_work(config, db_conn, accessToken, last_eff,
                                          focus_aliases=focus_aliases if in_focus else None)
                    except Exception as refresh_err:
                        last_err = str(refresh_err)
                        logger.error(f"Token refresh/retry failed: {refresh_err}", exc_info=True)
                        success = False
                round_s = time.monotonic() - round_t0

                rate_hits = get_rate_limit_hits()
                backoff.record_cycle(rate_hits, success)

                focus_state = {"active": in_focus}
                if in_focus:
                    health = _compute_health(round_s, focus_tick_s)
                    focus_state.update({
                        "experiment_id": focus_id,
                        "target_cadence_s": focus_tick_s,
                        "device_count": len(focus_aliases),
                        "last_round_s": round(round_s, 3),
                        "tick_utilization_pct": round(min(round_s / focus_tick_s * 100, 999.9), 1) if focus_tick_s else None,
                        "health": health,
                    })

                backoff.write_status_file(
                    control,
                    last_eff,
                    rate_hits=rate_hits,
                    cycle_completed=bool(success),
                    last_error=last_err or None,
                    focus_state=focus_state,
                )

                if success:
                    consecutive_failures = 0  # Reset failure counter on success
                else:
                    consecutive_failures += 1
                    logger.warning(f"Collection cycle failed ({consecutive_failures}/{max_consecutive_failures})")
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error(f"Too many consecutive failures ({consecutive_failures}), exiting")
                        sys.exit(1)

                # Sleep — tick-anchored when in Focus Mode (drift-free), else
                # plain sleep_for after the round (legacy behaviour).
                if in_focus:
                    if next_tick is None:
                        next_tick = round_t0 + focus_tick_s
                    else:
                        next_tick += focus_tick_s
                    if next_tick < time.monotonic():
                        # Round overran the tick — re-anchor to a future tick so
                        # the next sample lands at +N×tick from the original
                        # schedule, dropping in-between readings rather than
                        # widening cadence.
                        slack_neg = time.monotonic() - next_tick
                        slips = int(slack_neg // focus_tick_s) + 1
                        next_tick += slips * focus_tick_s
                        msg = (f"Tick slip: round took {round_s:.2f}s on {focus_tick_s}s tick "
                               f"(skipped {slips} tick(s)); cadence will be wider than configured")
                        logger.warning(msg)
                        try:
                            _record_admin_error_collector_side(source="focus_tick", message=msg)
                        except Exception:
                            pass
                    # Sleep precisely to the next_tick deadline — wake-up jitter
                    # is bounded by OS sleep granularity (≲10 ms), not by the
                    # cumulative overshoot of many short chunks.
                    _sleep_until_with_refresh_check(next_tick, accessToken)
                else:
                    next_tick = None
                    _sleep_with_refresh_check(last_eff["poll_interval"], accessToken)

            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down...")
                break
            except Exception as e:
                consecutive_failures += 1
                last_err = str(e)
                logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
                if consecutive_failures >= max_consecutive_failures:
                    logger.error(f"Too many consecutive failures ({consecutive_failures}), exiting")
                    sys.exit(1)
                sleep_s = (
                    last_eff["poll_interval"]
                    if last_eff
                    else _poll_interval_seconds(config)
                )
                _sleep_with_refresh_check(sleep_s, accessToken)

    finally:
        logger.info("Closing database connection...")
        try:
            db_conn.close()
        except:
            pass


if __name__ == "__main__":
    main()
