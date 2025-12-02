#!/usr/bin/env python3
"""
GOS Remote Energy Measurement (REM) Collector
Collects power consumption data from TP-Link Tapo P110 devices via Cloud API
"""

import os
import sys
import time
import calendar
import logging
import signal
import requests
import yaml
from pathlib import Path
from typing import List, Dict, Optional
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Configuration from environment variables
TPLINK_CLIENT_ID = os.getenv("TPLINK_CLIENT_ID", "fdcae128-0adf-4233-8a58-30760652bd16")
TPLINK_CLIENT_SECRET = os.getenv("TPLINK_CLIENT_SECRET", "4087d4b9-5e0c-4e50-b06c-22580fc618d5")
TPLINK_API_KEY = os.getenv("TPLINK_API_KEY", "e71bf02f-8b71-42ee-8af0-62a7bdf6c866")
TPLINK_REFRESH_TOKEN = os.getenv("TPLINK_REFRESH_TOKEN", "")

CONF_FILE = os.getenv("CONF_FILE", "/app/config/config.yaml")
TOKEN_FILE = os.getenv("TOKEN_FILE", "/app/data/refresh_token.txt")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))

# API endpoints
TPLINK_AUTH_URL = "https://aps1-openapi.tplinknbu.com/v1/oauth/token"
TPLINK_DEVICE_LIST_URL = "https://aps1-openapi.tplinknbu.com/v1/getDeviceList"
TPLINK_DEVICE_CONTROL_URL = "https://aps1-openapi.tplinknbu.com/v1/device/deviceControl"

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Global flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global running
    log.info(f"Received signal {signum}, shutting down gracefully...")
    running = False


# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def ensure_data_dir():
    """Ensure data directory exists for token storage"""
    token_path = Path(TOKEN_FILE)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    return token_path


def get_token() -> Optional[str]:
    """
    Get access token from TP-Link Cloud API.
    Uses refresh token from file or environment variable.
    """
    token_path = ensure_data_dir()
    
    # Get refresh token from file or environment
    refresh_token = TPLINK_REFRESH_TOKEN
    if not refresh_token and token_path.exists():
        try:
            refresh_token = token_path.read_text().strip()
            log.debug(f"Loaded refresh token from {token_path}")
        except Exception as e:
            log.error(f"Failed to read token file: {e}")
            refresh_token = None
    
    if not refresh_token:
        log.error("No refresh token available. Please set TPLINK_REFRESH_TOKEN environment variable or provide token file.")
        return None
    
    # Refresh access token
    try:
        auth_data = {
            'client_id': TPLINK_CLIENT_ID,
            'grant_type': 'refresh_token',
            'client_secret': TPLINK_CLIENT_SECRET,
            'refresh_token': refresh_token
        }
        
        response = requests.post(TPLINK_AUTH_URL, data=auth_data, timeout=10)
        response.raise_for_status()
        tokens = response.json()
        
        access_token = tokens.get("accessToken")
        new_refresh_token = tokens.get("refreshToken")
        
        if not access_token:
            log.error("Failed to get access token from API response")
            return None
        
        # Save new refresh token
        if new_refresh_token and new_refresh_token != refresh_token:
            try:
                token_path.write_text(new_refresh_token)
                log.debug(f"Updated refresh token in {token_path}")
            except Exception as e:
                log.warning(f"Failed to save refresh token: {e}")
        
        log.debug("Successfully refreshed access token")
        return access_token
        
    except requests.exceptions.RequestException as e:
        log.error(f"Failed to refresh token: {e}")
        return None
    except Exception as e:
        log.error(f"Unexpected error getting token: {e}")
        return None


def get_device_list(access_token: str) -> List[Dict[str, str]]:
    """
    Get list of online P110/P110M devices from TP-Link Cloud API.
    Returns list of devices with deviceId and alias.
    """
    try:
        data = {
            'client_id': TPLINK_CLIENT_ID,
            'api_key': TPLINK_API_KEY,
            'token': access_token
        }
        
        response = requests.post(TPLINK_DEVICE_LIST_URL, data=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        devices = []
        for item in result.get("devices", []):
            # Only include online P110/P110M devices
            if item.get('online') is not False and item.get('model') in ('P110', 'P110M'):
                devices.append({
                    'deviceId': item['deviceId'],
                    'alias': item.get('alias', 'Unknown')
                })
        
        log.info(f"Found {len(devices)} online P110 devices")
        return devices
        
    except requests.exceptions.RequestException as e:
        log.error(f"Failed to get device list: {e}")
        return []
    except Exception as e:
        log.error(f"Unexpected error getting device list: {e}")
        return []


def get_device_power(device_id: str, access_token: str) -> Optional[float]:
    """
    Get real-time power consumption from a specific device.
    Returns power in watts, or None on error.
    """
    try:
        url = f"{TPLINK_DEVICE_CONTROL_URL}?client_id={TPLINK_CLIENT_ID}&api_key={TPLINK_API_KEY}&token={access_token}"
        data = {
            "method": "getDeviceRealTimeEnergy",
            "device": {"id": device_id}
        }
        
        session = requests.Session()
        session.headers.update({'Content-Type': 'application/json'})
        response = session.post(url, json=data, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        power_watts = result.get('result', {}).get('powerWatts')
        
        if power_watts is None:
            log.warning(f"Device {device_id} returned no power reading")
            return None
            
        return float(power_watts)
        
    except requests.exceptions.RequestException as e:
        log.warning(f"Failed to get power for device {device_id}: {e}")
        return None
    except (ValueError, KeyError) as e:
        log.warning(f"Invalid response for device {device_id}: {e}")
        return None
    except Exception as e:
        log.error(f"Unexpected error getting power for device {device_id}: {e}")
        return None


def write_to_influxdb(write_api, bucket: str, org: str, device_id: str, alias: str, power_watts: float):
    """Write a single data point to InfluxDB"""
    try:
        timestamp = time.time_ns()
        point = Point("gos_rem") \
            .tag("alias", alias) \
            .field("powerWatts", float(power_watts)) \
            .time(timestamp)
        
        write_api.write(bucket=bucket, org=org, record=point)
        log.debug(f"Wrote {power_watts}W for {alias} ({device_id})")
        return True
        
    except Exception as e:
        log.error(f"Failed to write to InfluxDB for {alias}: {e}")
        return False


def load_config() -> Optional[Dict]:
    """Load configuration from YAML file"""
    config_path = Path(CONF_FILE)
    
    if not config_path.exists():
        log.warning(f"Config file not found at {CONF_FILE}, using defaults")
        return {
            'poller': {
                'persist': True,
                'interval': POLL_INTERVAL
            },
            'influxdb': [{
                'name': 'local',
                'url': os.getenv('INFLUXDB_URL', 'http://influxdb:8086'),
                'org': os.getenv('INFLUXDB_ORG', 'GOS'),
                'bucket': os.getenv('INFLUXDB_BUCKET', 'rem'),
                'token': os.getenv('INFLUXDB_TOKEN', '')
            }]
        }
    
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        # Override with environment variables if set
        if 'influxdb' in config and len(config['influxdb']) > 0:
            influx_config = config['influxdb'][0]
            influx_config['url'] = os.getenv('INFLUXDB_URL', influx_config.get('url', 'http://influxdb:8086'))
            influx_config['org'] = os.getenv('INFLUXDB_ORG', influx_config.get('org', 'GOS'))
            influx_config['bucket'] = os.getenv('INFLUXDB_BUCKET', influx_config.get('bucket', 'rem'))
            influx_config['token'] = os.getenv('INFLUXDB_TOKEN', influx_config.get('token', ''))
        
        # Override poller interval from environment
        if 'poller' in config:
            config['poller']['interval'] = int(os.getenv('POLL_INTERVAL', config['poller'].get('interval', 30)))
        
        return config
        
    except yaml.YAMLError as e:
        log.error(f"Failed to parse config file: {e}")
        return None
    except Exception as e:
        log.error(f"Failed to load config: {e}")
        return None


def collect_data(config: Dict, influxes: List[Dict], access_token: str):
    """Main data collection function"""
    # Get device list
    devices = get_device_list(access_token)
    
    if not devices:
        log.warning("No devices found or failed to get device list")
        return
    
    # Collect power readings for each device
    points_written = 0
    for device in devices:
        if not running:
            break
            
        device_id = device['deviceId']
        alias = device['alias']
        
        # Get power reading
        power_watts = get_device_power(device_id, access_token)
        
        if power_watts is None:
            continue
        
        # Write to all configured InfluxDB instances
        for influx in influxes:
            try:
                write_api = influx['conn'].write_api(write_options=SYNCHRONOUS)
                if write_to_influxdb(
                    write_api,
                    influx['bucket'],
                    influx['org'],
                    device_id,
                    alias,
                    power_watts
                ):
                    points_written += 1
            except Exception as e:
                log.error(f"Failed to write to {influx['name']}: {e}")
        
        log.info(f"Collected {power_watts}W from {alias}")
    
    if points_written > 0:
        log.info(f"Successfully wrote {points_written} data points to InfluxDB")


def main():
    """Main entry point"""
    global running
    
    log.info("Starting GOS Remote Energy Measurement Collector")
    log.info(f"Poll interval: {POLL_INTERVAL} seconds")
    log.info(f"Log level: {LOG_LEVEL}")
    
    # Load configuration
    config = load_config()
    if not config:
        log.error("Failed to load configuration, exiting")
        sys.exit(1)
    
    # Get access token
    access_token = get_token()
    if not access_token:
        log.error("Failed to get access token, exiting")
        sys.exit(1)
    
    # Setup InfluxDB connections
    influxes = []
    for influx_config in config.get('influxdb', []):
        try:
            client = InfluxDBClient(
                url=influx_config['url'],
                token=influx_config.get('token', ''),
                org=influx_config.get('org', 'GOS')
            )
            
            influxes.append({
                'name': influx_config.get('name', 'default'),
                'bucket': influx_config.get('bucket', 'rem'),
                'org': influx_config.get('org', 'GOS'),
                'conn': client
            })
            
            log.info(f"Configured InfluxDB connection: {influx_config.get('name', 'default')} at {influx_config['url']}")
            
        except Exception as e:
            log.error(f"Failed to setup InfluxDB connection {influx_config.get('name', 'default')}: {e}")
    
    if not influxes:
        log.error("No valid InfluxDB connections configured, exiting")
        sys.exit(1)
    
    # Determine if we should run in persistent mode
    persist = config.get('poller', {}).get('persist', True)
    interval = config.get('poller', {}).get('interval', POLL_INTERVAL)
    
    if not persist:
        # Single run
        log.info("Running in one-shot mode")
        collect_data(config, influxes, access_token)
        log.info("Collection complete, exiting")
        return
    
    # Persistent mode - run in loop
    log.info(f"Running in persistent mode (interval: {interval}s)")
    token_refresh_interval = 3600  # Refresh token every hour
    
    last_token_refresh = time.time()
    
    try:
        while running:
            # Refresh token periodically
            if time.time() - last_token_refresh > token_refresh_interval:
                log.info("Refreshing access token...")
                new_token = get_token()
                if new_token:
                    access_token = new_token
                    last_token_refresh = time.time()
                else:
                    log.error("Failed to refresh token, will retry on next cycle")
            
            # Collect data
            collect_data(config, influxes, access_token)
            
            # Sleep until next interval (or until interrupted)
            for _ in range(interval):
                if not running:
                    break
                time.sleep(1)
                
    except KeyboardInterrupt:
        log.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        log.error(f"Unexpected error in main loop: {e}", exc_info=True)
    finally:
        # Cleanup
        log.info("Cleaning up connections...")
        for influx in influxes:
            try:
                influx['conn'].close()
            except:
                pass
        log.info("Shutdown complete")


if __name__ == "__main__":
    main()

