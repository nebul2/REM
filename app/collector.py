#!/usr/bin/env python3
import requests
import calendar
import time
import logging
import os
import sys
import yaml
import psycopg2
from psycopg2.extras import execute_values

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CONF_FILE = os.getenv("CONF_FILE", "/app/config/config.yaml")

#visit this in browser first to get the 'code'
# https://aps1-openapi.tplinknbu.com/v1/oauth/authorize?client_id=fdcae128-0adf-4233-8a58-30760652bd16&response_type=code&scope=all&state=123456789012345678901234&redirect_uri=https://www.greeningofstreaming.org

def getToken():
    #load refreshToken from environment variable or file
    refreshToken = os.getenv("TPLINK_REFRESH_TOKEN", "")
    
    # If not in env, try to read from file (for backward compatibility)
    if not refreshToken:
        token_file = os.getenv("TOKEN_FILE", "/app/data/refresh_token.txt")
        if os.path.exists(token_file):
            try:
                with open(token_file, "r") as f:
                    refreshToken = f.readline().strip()
            except:
                pass

    if len(refreshToken) >= 2: #if refreshToken then use to get accessToken
        authurl='https://aps1-openapi.tplinknbu.com/v1/oauth/token'
        getTokendata = {'client_id': 'fdcae128-0adf-4233-8a58-30760652bd16', 'grant_type': 'refresh_token', 'client_secret': '4087d4b9-5e0c-4e50-b06c-22580fc618d5', 'refresh_token': refreshToken}
        tokenResponse = requests.post(authurl, data=getTokendata)
        tokensjson = tokenResponse.json()
        accessToken=tokensjson["accessToken"]
        refreshToken=tokensjson["refreshToken"]

    else:    #if no refreshToken then ask user for manual code
        inputcode=input("Paste Code:")
        authurl='https://aps1-openapi.tplinknbu.com/v1/oauth/token'
        getTokendata = {'client_id': 'fdcae128-0adf-4233-8a58-30760652bd16', 'grant_type': 'code', 'client_secret': '4087d4b9-5e0c-4e50-b06c-22580fc618d5', 'code': inputcode}
        tokenResponse = requests.post(authurl, data=getTokendata)
        tokensjson = tokenResponse.json()
        accessToken=tokensjson["accessToken"]
        refreshToken=tokensjson["refreshToken"]

    print(accessToken)
    print(refreshToken)

    # Save new refresh token to file for persistence
    token_file = os.getenv("TOKEN_FILE", "/app/data/refresh_token.txt")
    try:
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        with open(token_file, "w") as f:
            f.write(refreshToken)
    except Exception as e:
        print(f"Warning: Could not save refresh token to {token_file}: {e}")

    return accessToken

def getDeviceIdList(accessToken):

    devListurl='https://aps1-openapi.tplinknbu.com/v1/getDeviceList?'
    getDevlistdata={'client_id': 'fdcae128-0adf-4233-8a58-30760652bd16', 'api_key': 'e71bf02f-8b71-42ee-8af0-62a7bdf6c866', 'token': accessToken}
    devList = requests.post(devListurl, data=getDevlistdata)
    print(devList.json())

    deviceIdList =[]
    for item in devList.json()["devices"]:
        if item['online'] != False and item['model'] in('P110' ,'P110M'):
            deviceIdList.append({'deviceId': item['deviceId'],
                                    'alias': item['alias']})
    
    print(deviceIdList)
    return deviceIdList


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


def getDevicePowerList(deviceIdList, accessToken, config, db_conn):
    """Poll all devices and write valid readings to database. Skips failed devices."""
    devicePowerList = []
    points_buffer = []
    failed_devices = []
    
    # Rate limit delay between device queries (seconds) to avoid API throttling
    # Read from collector control file if available, otherwise use config or default
    device_query_delay = 0.5  # Default
    control_file = "/app/data/collector_control.json"
    try:
        if os.path.exists(control_file):
            import json
            with open(control_file, 'r') as f:
                control = json.load(f)
                device_query_delay = control.get("device_query_delay", 0.5)
    except Exception as e:
        logger.warning(f"Could not read device_query_delay from control file: {e}")
    
    #walk through each device reading power
    for item in deviceIdList:
        device_id = item['deviceId']
        alias = item['alias']
        
        devPower = getDevPower(device_id, accessToken)
        
        # Skip devices that failed to respond
        if devPower is None:
            failed_devices.append(alias)
            if device_query_delay > 0:
                time.sleep(device_query_delay)  # Still delay to avoid hammering API on failures
            continue
        
        current_GMT = time.gmtime()
        timestamp = calendar.timegm(current_GMT)
        
        # Store data point for batch insert (only valid readings)
        points_buffer.append({
            'alias': alias,
            'power_watts': float(devPower),
            'time': timestamp
        })
        
        # Rate limit: delay between device queries to avoid API throttling (429 errors)
        if device_query_delay > 0:
            time.sleep(device_query_delay)
    
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
    #lets go get a list of the devices and their power
    pollCloud(config, db_conn, accessToken)
    return


def sendToTimescaleDB(db_conn, points_buffer):
    ''' Take a set of values, and send them to TimescaleDB
    '''
    try:
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
    except Exception as e:
        print(f"Failed to write to TimescaleDB: {e}")
        db_conn.rollback()
        return False


def get_db_connection(config):
    ''' Create PostgreSQL/TimescaleDB connection
    '''
    # Read connection parameters from environment variables or config
    host = os.getenv("POSTGRES_HOST", config.get("postgresql", {}).get("host", "timescaledb"))
    port = os.getenv("POSTGRES_PORT", config.get("postgresql", {}).get("port", "5432"))
    database = os.getenv("POSTGRES_DB", config.get("postgresql", {}).get("database", "gos_rem"))
    user = os.getenv("POSTGRES_USER", config.get("postgresql", {}).get("user", "gos"))
    password = os.getenv("POSTGRES_PASSWORD", config.get("postgresql", {}).get("password", ""))
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        return conn
    except Exception as e:
        print(f"Failed to connect to TimescaleDB: {e}")
        return None


def main():
    accessToken = getToken()

    config = load_config()
    if not config:
       sys.exit(1)

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
        do_work(config, db_conn, accessToken)
        db_conn.close()
        return

    # Otherwise, set up a loop and poll periodically
    try:
        while True:
            do_work(config, db_conn, accessToken)
            time.sleep(int(config["poller"]["interval"]))
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        db_conn.close()


if __name__ == "__main__":
    main()
