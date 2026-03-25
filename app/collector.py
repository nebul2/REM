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

_logged_poll_interval = None


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
        resp = devList.json()
    except Exception as e:
        logger.error(f"TP-Link getDeviceList request failed: {e}")
        return []

    if resp.get('errorCode') == TOKEN_INVALID_ERROR_CODE or str(resp.get("errMessage", "")).lower() == "token invalid":
        raise TokenInvalidError(f"TP-Link token invalid: {resp}")

    if resp.get('errorCode') or resp.get('error'):
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
        
        # Add timeout to prevent hanging
        devPowerlist = session.post(devPowerurl, json=getDevpowerlistdata, timeout=10)
        
        # Check if request was successful
        devPowerlist.raise_for_status()
        
        response_json = devPowerlist.json()
        
        # Check if response has expected structure
        if 'result' not in response_json or 'powerWatts' not in response_json.get('result', {}):
            logger.warning(f"Unexpected API response structure for device {deviceId}: {response_json}")
            return None
        
        power_watts = response_json['result']['powerWatts']
        
        # Validate the value is numeric
        try:
            power_float = float(power_watts)
            # Reject negative values (power can't be negative)
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


def getDevicePowerList(deviceIdList, accessToken, config, db_conn):
    """Poll all devices and write valid readings to database. Skips failed devices."""
    devicePowerList = []
    points_buffer = []
    failed_devices = []
    
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

    parallel_workers = _parse_parallel_workers(control)

    if parallel_workers <= 1:
        # Legacy sequential path (one HTTP at a time)
        for item in deviceIdList:
            device_id = item['deviceId']
            alias = item['alias']
            
            devPower = getDevPower(device_id, accessToken)
            
            if devPower is None:
                failed_devices.append(alias)
                if device_query_delay > 0:
                    time.sleep(device_query_delay)
                continue
            
            current_GMT = time.gmtime()
            timestamp = calendar.timegm(current_GMT)
            
            points_buffer.append({
                'alias': alias,
                'power_watts': float(devPower),
                'time': timestamp
            })
            
            if device_query_delay > 0:
                time.sleep(device_query_delay)
    else:
        # Parallel: up to `parallel_workers` concurrent TP-Link calls per chunk; optional delay between chunks
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
                    points_buffer.append({
                        'alias': alias,
                        'power_watts': float(devPower),
                        'time': timestamp
                    })
            if device_query_delay > 0 and ci < len(chunks) - 1:
                time.sleep(device_query_delay)
        if parallel_workers > 1:
            logger.info(
                "Parallel device polling: up to %d workers per chunk, %d chunk(s), inter-chunk delay %ss",
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


def pollCloud(config, db_conn, accessToken):
    deviceIdList = getDeviceIdList(accessToken)
    devicePowerList = getDevicePowerList(deviceIdList, accessToken, config, db_conn)
    return 


def do_work(config, db_conn, accessToken):
    """Execute one collection cycle. Returns True on success, False on failure."""
    try:
        #lets go get a list of the devices and their power
        pollCloud(config, db_conn, accessToken)
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
        # Trigger the poller as a one-shot thing
        try:
            do_work(config, db_conn, accessToken)
        except TokenInvalidError:
            logger.warning("TP-Link token invalid in one-shot mode, refreshing token and retrying once")
            accessToken = getToken()
            do_work(config, db_conn, accessToken)
        db_conn.close()
        return

    # Otherwise, set up a loop and poll periodically
    consecutive_failures = 0
    max_consecutive_failures = 10  # Exit after 10 consecutive failures
    
    try:
        while True:
            try:
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
                        time.sleep(_poll_interval_seconds(config))
                        continue
                    logger.info("Successfully reconnected to database")
                
                # Execute collection cycle
                try:
                    success = do_work(config, db_conn, accessToken)
                except TokenInvalidError:
                    logger.warning("TP-Link token invalid, refreshing access token and retrying cycle")
                    try:
                        accessToken = getToken()
                        success = do_work(config, db_conn, accessToken)
                    except Exception as refresh_err:
                        logger.error(f"Token refresh/retry failed: {refresh_err}", exc_info=True)
                        success = False
                
                if success:
                    consecutive_failures = 0  # Reset failure counter on success
                else:
                    consecutive_failures += 1
                    logger.warning(f"Collection cycle failed ({consecutive_failures}/{max_consecutive_failures})")
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error(f"Too many consecutive failures ({consecutive_failures}), exiting")
                        sys.exit(1)
                
                time.sleep(_poll_interval_seconds(config))
                
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down...")
                break
            except Exception as e:
                consecutive_failures += 1
                logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
                if consecutive_failures >= max_consecutive_failures:
                    logger.error(f"Too many consecutive failures ({consecutive_failures}), exiting")
                    sys.exit(1)
                # Wait before retrying after an error
                time.sleep(_poll_interval_seconds(config))
                
    finally:
        logger.info("Closing database connection...")
        try:
            db_conn.close()
        except:
            pass


if __name__ == "__main__":
    main()
