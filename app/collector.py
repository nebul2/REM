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
    return {
        "enabled": True,
        "poll_interval": 30,
        "device_query_delay": 0.5,
        "parallel_workers": 8,
        "adaptive_backoff": True,
    }


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
            current_GMT = time.gmtime()
            timestamp = calendar.timegm(current_GMT)
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
                    current_GMT = time.gmtime()
                    timestamp = calendar.timegm(current_GMT)
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


def pollCloud(config, db_conn, accessToken, eff):
    """eff: dict from AdaptiveBackoff.effective() with parallel_workers and device_query_delay."""
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

    getDevicePowerList(
        deviceIdList,
        accessToken,
        config,
        db_conn,
        parallel_workers_override=eff.get("parallel_workers"),
        device_query_delay_override=eff.get("device_query_delay"),
    )


def do_work(config, db_conn, accessToken, eff):
    """Execute one collection cycle. Returns True on success, False on failure."""
    try:
        pollCloud(config, db_conn, accessToken, eff)
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
        
        # Prepare data for batch insert
        values = []
        for point in points_buffer:
            # Convert timestamp to PostgreSQL timestamptz
            ts = time.strftime('%Y-%m-%d %H:%M:%S+00', time.gmtime(point['time']))
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
                        time.sleep(sleep_s)
                        continue
                    logger.info("Successfully reconnected to database")

                last_err = ""
                try:
                    success = do_work(config, db_conn, accessToken, last_eff)
                except TokenInvalidError:
                    logger.warning("TP-Link token invalid, refreshing access token and retrying cycle")
                    try:
                        accessToken = getToken()
                        success = do_work(config, db_conn, accessToken, last_eff)
                    except Exception as refresh_err:
                        last_err = str(refresh_err)
                        logger.error(f"Token refresh/retry failed: {refresh_err}", exc_info=True)
                        success = False

                rate_hits = get_rate_limit_hits()
                backoff.record_cycle(rate_hits, success)
                backoff.write_status_file(
                    control,
                    last_eff,
                    rate_hits=rate_hits,
                    cycle_completed=bool(success),
                    last_error=last_err or None,
                )

                if success:
                    consecutive_failures = 0  # Reset failure counter on success
                else:
                    consecutive_failures += 1
                    logger.warning(f"Collection cycle failed ({consecutive_failures}/{max_consecutive_failures})")
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error(f"Too many consecutive failures ({consecutive_failures}), exiting")
                        sys.exit(1)

                sleep_s = last_eff["poll_interval"]
                time.sleep(sleep_s)

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
                time.sleep(sleep_s)
                
    finally:
        logger.info("Closing database connection...")
        try:
            db_conn.close()
        except:
            pass


if __name__ == "__main__":
    main()
