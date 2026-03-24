"""
GOS REM Data Exploration Tool - Complete Integrated Backend API
Combines group management and data exploration functionality
"""
from fastapi import FastAPI, Request, Form, HTTPException, Query, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import json
import os
import re
import uuid
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
import shutil
import tempfile
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
import pandas as pd
import base64
import zipfile
from io import BytesIO, StringIO
import csv
import secrets

app = FastAPI(title="GOS REM Data Exploration Tool", root_path="")

# Add CORS middleware to allow healthcheck from dashboard
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for healthcheck
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional HTTP Basic Auth for UI/APIs (enabled when both env vars are set)
ADMIN_BASIC_USER = os.getenv("ADMIN_BASIC_USER", "").strip()
ADMIN_BASIC_PASSWORD = os.getenv("ADMIN_BASIC_PASSWORD", "").strip()


def _basic_auth_enabled() -> bool:
    return bool(ADMIN_BASIC_USER and ADMIN_BASIC_PASSWORD)


@app.middleware("http")
async def basic_auth_middleware(request: Request, call_next):
    # Only enforce auth if both username and password are configured
    if not _basic_auth_enabled():
        return await call_next(request)

    path = request.url.path

    # Paths that must remain unauthenticated
    if path.startswith("/health") or path.startswith("/static") or path.startswith("/api/static"):
        return await call_next(request)

    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("basic "):
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": "Basic"},
            content="Unauthorized",
        )

    try:
        encoded = auth.split(" ", 1)[1]
        decoded = base64.b64decode(encoded).decode("utf-8")
        username, password = decoded.split(":", 1)
    except Exception:
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": "Basic"},
            content="Unauthorized",
        )

    if not (
        secrets.compare_digest(username, ADMIN_BASIC_USER)
        and secrets.compare_digest(password, ADMIN_BASIC_PASSWORD)
    ):
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": "Basic"},
            content="Unauthorized",
        )

    return await call_next(request)

# Templates and static files
templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"
templates = Jinja2Templates(directory=str(templates_dir))

# Mount static files - serve from multiple paths to bypass auth
app.mount("/static", StaticFiles(directory=str(static_dir), html=False), name="static")
# Also mount at root level for direct access
static_files = StaticFiles(directory=str(static_dir), html=False)
app.mount("/assets", static_files, name="assets")

# Add no-cache headers for static files
@app.middleware("http")
async def add_no_cache_header(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Data directory
DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
GROUPS_FILE = DATA_DIR / "device_groups.json"
EXPERIMENTS_FILE = DATA_DIR / "experiments.json"
ANNOTATIONS_FILE = DATA_DIR / "annotations.json"
SNAPSHOTS_FILE = DATA_DIR / "snapshots.json"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
COLLECTOR_CONTROL_FILE = DATA_DIR / "collector_control.json"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# PostgreSQL/TimescaleDB connection
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "timescaledb")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "gos_rem")
POSTGRES_USER = os.getenv("POSTGRES_USER", "gos")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")


def get_db_connection(timeout_seconds=300):
    """Get PostgreSQL/TimescaleDB connection with configurable timeout"""
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            connect_timeout=10,
            options=f"-c statement_timeout={timeout_seconds * 1000}"  # Convert to milliseconds
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

# ============================================================================
# Helper Functions - Static Asset Loading
# ============================================================================

def load_all_css() -> str:
    """Load and combine all CSS files"""
    css_files = [
        static_dir / "exploration.css",
        static_dir / "style.css"
    ]
    combined_css = ""
    for css_file in css_files:
        if css_file.exists():
            combined_css += css_file.read_text() + "\n"
    return combined_css

def load_js_file(js_filename: str) -> str:
    """Load a JavaScript file"""
    js_file = static_dir / js_filename
    if js_file.exists():
        return js_file.read_text()
    return ""

def get_logo_data_uri() -> str:
    """Get base64 data URI for logo"""
    logo_path = static_dir / "gos-logo.png"
    if logo_path.exists():
        with open(logo_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')
            return f"data:image/png;base64,{img_data}"
    return ""

# ============================================================================
# Helper Functions - Data Loading/Saving
# ============================================================================

def load_groups() -> dict:
    """Load device groups from JSON file"""
    if GROUPS_FILE.exists():
        try:
            with open(GROUPS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading groups: {e}")
            return {}
    return {}


def save_groups(groups: dict):
    """Save device groups to JSON file"""
    try:
        GROUPS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(GROUPS_FILE, 'w') as f:
            json.dump(groups, f, indent=2)
    except Exception as e:
        print(f"Error saving groups: {e}")


def load_experiments() -> dict:
    """Load experiments from JSON file"""
    if EXPERIMENTS_FILE.exists():
        try:
            with open(EXPERIMENTS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading experiments: {e}")
            return {}
    return {}


def save_experiments(experiments: dict):
    """Save experiments to JSON file"""
    try:
        EXPERIMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(EXPERIMENTS_FILE, 'w') as f:
            json.dump(experiments, f, indent=2)
    except Exception as e:
        print(f"Error saving experiments: {e}")


def load_annotations() -> dict:
    """Load annotations from JSON file"""
    if ANNOTATIONS_FILE.exists():
        try:
            with open(ANNOTATIONS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading annotations: {e}")
            return {}
    return {}


def save_annotations(annotations: dict):
    """Save annotations to JSON file"""
    try:
        ANNOTATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ANNOTATIONS_FILE, 'w') as f:
            json.dump(annotations, f, indent=2)
    except Exception as e:
        print(f"Error saving annotations: {e}")


def load_snapshots() -> dict:
    """Load snapshots from JSON file"""
    if SNAPSHOTS_FILE.exists():
        try:
            with open(SNAPSHOTS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading snapshots: {e}")
            return {}
    return {}


def save_snapshots(snapshots: dict):
    """Save snapshots to JSON file"""
    try:
        SNAPSHOTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SNAPSHOTS_FILE, 'w') as f:
            json.dump(snapshots, f, indent=2)
    except Exception as e:
        print(f"Error saving snapshots: {e}")


# ============================================================================
# Helper Functions - Database Queries
# ============================================================================

def get_available_devices() -> List[str]:
    """Get list of available devices from TimescaleDB"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First try last 24 hours, if no results, try last 7 days
        query = """
        SELECT DISTINCT alias 
        FROM gos_rem 
        WHERE time >= NOW() - INTERVAL '24 hours'
        ORDER BY alias
        """
        cursor.execute(query)
        devices = [row[0] for row in cursor.fetchall()]
        
        # If no devices in last 24 hours, look back 7 days
        if not devices:
            query = """
            SELECT DISTINCT alias 
            FROM gos_rem 
            WHERE time >= NOW() - INTERVAL '7 days'
            ORDER BY alias
            """
            cursor.execute(query)
            devices = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        return sorted(devices)
    except HTTPException:
        # Re-raise HTTPException to allow proper error handling upstream
        raise
    except Exception as e:
        print(f"Error fetching devices: {e}")
        return []


def query_power_data(devices: List[str], start_time: str, end_time: str, interval: str = "1m", timeout_seconds: int = 120) -> Dict[str, Any]:
    """Query power consumption data from TimescaleDB with configurable timeout"""
    try:
        # Use shorter timeout for very large queries to fail faster and provide better error messages
        conn = get_db_connection(timeout_seconds=timeout_seconds)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        SELECT 
          time_bucket(%s, time) AS time,
          alias,
          AVG(power_watts) AS power_watts
        FROM gos_rem
        WHERE time >= %s 
          AND time <= %s
          AND alias = ANY(%s)
        GROUP BY time_bucket(%s, time), alias
        ORDER BY time, alias;
        """
        
        # Convert interval to TimescaleDB format (e.g., '1 minute')
        # Supporting intervals like '10s', '30s', '1m', '5m', '1h'
        interval_map = {
            "10s": "10 seconds", "30s": "30 seconds",
            "1m": "1 minute", "5m": "5 minutes", "15m": "15 minutes",
            "30m": "30 minutes", "1h": "1 hour", "6h": "6 hours",
            "12h": "12 hours", "1d": "1 day"
        }
        pg_interval = interval_map.get(interval, "1 minute") # Default to 1 minute
        
        # Convert start_time and end_time to datetime objects
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        cursor.execute(query, (pg_interval, start_dt, end_dt, devices, pg_interval))
        
        records = cursor.fetchall()
        
        data_points = []
        device_data = {}
        
        for record in records:
            timestamp = record["time"].isoformat()
            alias = record["alias"]
            value = record["power_watts"]
            
            if alias and value is not None:
                if alias not in device_data:
                    device_data[alias] = []
                device_data[alias].append({"timestamp": timestamp, "value": float(value)})
        
        cursor.close()
        conn.close()
        
        # Generate all expected time buckets (even if empty) for forward-fill to work
        from datetime import timedelta
        import re
        
        # Parse interval to generate all expected buckets
        num = 1
        unit = 'm'
        interval_match = re.match(r'(\d+)([smhd])', interval.lower())
        if interval_match:
            num = int(interval_match.group(1))
            unit = interval_match.group(2)
            if unit == 's':
                bucket_delta = timedelta(seconds=num)
            elif unit == 'm':
                bucket_delta = timedelta(minutes=num)
            elif unit == 'h':
                bucket_delta = timedelta(hours=num)
            elif unit == 'd':
                bucket_delta = timedelta(days=num)
            else:
                bucket_delta = timedelta(minutes=1)
        else:
            bucket_delta = timedelta(minutes=1)
        
        # Estimate number of data points to decide if we should generate all buckets
        time_range_seconds = (end_dt - start_dt).total_seconds()
        bucket_seconds = bucket_delta.total_seconds()
        estimated_buckets = int(time_range_seconds / bucket_seconds) if bucket_seconds > 0 else 0
        total_estimated_points = estimated_buckets * len(device_data.keys()) if device_data else 0
        
        # Only generate all time buckets for small datasets (< 50k points) to avoid memory/timeout issues
        # For large datasets, just return the data that exists (no forward-fill)
        if total_estimated_points < 50000:
            # Generate all expected time buckets from start to end
            # Align to proper interval boundaries (e.g., for 5m intervals: :00, :05, :10, etc.)
            expected_timestamps = []
            current_time = start_dt
            
            # Align start time to the nearest interval boundary
            if unit == 's':
                # For seconds, align to the second boundary
                current_time = current_time.replace(microsecond=0)
                # Round down to nearest interval boundary
                seconds_offset = current_time.second % num
                if seconds_offset > 0:
                    current_time = current_time.replace(second=current_time.second - seconds_offset)
            elif unit == 'm':
                # For minutes, align to the minute boundary and then to interval
                current_time = current_time.replace(second=0, microsecond=0)
                # Round down to nearest interval boundary
                minutes_offset = current_time.minute % num
                if minutes_offset > 0:
                    current_time = current_time.replace(minute=current_time.minute - minutes_offset)
            elif unit == 'h':
                # For hours, align to the hour boundary and then to interval
                current_time = current_time.replace(minute=0, second=0, microsecond=0)
                # Round down to nearest interval boundary
                hours_offset = current_time.hour % num
                if hours_offset > 0:
                    current_time = current_time.replace(hour=current_time.hour - hours_offset)
            elif unit == 'd':
                # For days, align to midnight and then to interval
                current_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            while current_time <= end_dt:
                expected_timestamps.append(current_time.isoformat())
                current_time += bucket_delta
            
            # Organize existing data by timestamp
            # Normalize timestamps to ISO format for matching
            existing_by_timestamp = {}
            for device, points in device_data.items():
                for point in points:
                    # Normalize timestamp to ISO format (handle both formats from DB)
                    ts_raw = point["timestamp"]
                    if isinstance(ts_raw, str):
                        # Parse and re-format to ensure consistent format
                        try:
                            ts_dt = datetime.fromisoformat(ts_raw.replace('Z', '+00:00'))
                            ts = ts_dt.isoformat()
                        except:
                            ts = ts_raw
                    else:
                        ts = ts_raw.isoformat() if hasattr(ts_raw, 'isoformat') else str(ts_raw)
                    
                    if ts not in existing_by_timestamp:
                        existing_by_timestamp[ts] = {}
                    existing_by_timestamp[ts][device] = point["value"]
            
            # Create data points for ALL expected time buckets (including empty ones)
            for ts in expected_timestamps:
                # Normalize expected timestamp for comparison
                ts_normalized = ts
                if isinstance(ts, str):
                    try:
                        ts_dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        ts_normalized = ts_dt.isoformat()
                    except:
                        ts_normalized = ts
                
                point = {"timestamp": ts_normalized}
                # Add data for all devices (None if missing)
                for device in device_data.keys():
                    # Try exact match first, then try without microseconds/seconds for flexibility
                    if ts_normalized in existing_by_timestamp and device in existing_by_timestamp[ts_normalized]:
                        point[device] = existing_by_timestamp[ts_normalized][device]
                    else:
                        # Try matching with slightly different timestamp formats
                        matched = False
                        for db_ts in existing_by_timestamp.keys():
                            # Compare timestamps (allow small differences in format)
                            try:
                                db_dt = datetime.fromisoformat(db_ts.replace('Z', '+00:00'))
                                exp_dt = datetime.fromisoformat(ts_normalized.replace('Z', '+00:00'))
                                if abs((db_dt - exp_dt).total_seconds()) < 60:  # Within 1 minute
                                    if device in existing_by_timestamp[db_ts]:
                                        point[device] = existing_by_timestamp[db_ts][device]
                                        matched = True
                                        break
                            except:
                                pass
                        
                        if not matched:
                            point[device] = None
                
                # Include ALL time buckets (even if empty) so forward-fill can work
                data_points.append(point)
        else:
            # Large dataset: just return the data we have, organized by timestamp
            all_timestamps = set()
            for device, points in device_data.items():
                for point in points:
                    ts_raw = point["timestamp"]
                    if isinstance(ts_raw, str):
                        try:
                            ts_dt = datetime.fromisoformat(ts_raw.replace('Z', '+00:00'))
                            all_timestamps.add(ts_dt.isoformat())
                        except:
                            all_timestamps.add(ts_raw)
                    else:
                        all_timestamps.add(ts_raw.isoformat() if hasattr(ts_raw, 'isoformat') else str(ts_raw))
            
            # Create data points only for timestamps that exist
            for ts in sorted(all_timestamps):
                point = {"timestamp": ts}
                for device in device_data.keys():
                    # Find matching data point
                    found_value = None
                    for device_points in device_data[device]:
                        device_ts = device_points["timestamp"]
                        if isinstance(device_ts, str):
                            try:
                                device_ts_dt = datetime.fromisoformat(device_ts.replace('Z', '+00:00'))
                                device_ts = device_ts_dt.isoformat()
                            except:
                                pass
                        else:
                            device_ts = device_ts.isoformat() if hasattr(device_ts, 'isoformat') else str(device_ts)
                        
                        if device_ts == ts:
                            found_value = device_points["value"]
                            break
                    
                    point[device] = found_value
                
                data_points.append(point)
        
        return {
            "data": data_points,
            "devices": sorted(device_data.keys())
        }
    
    except Exception as e:
        print(f"Error querying power data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query data: {str(e)}")


def _parse_iso_to_utc_aware(iso_str: str) -> datetime:
    """Parse ISO timestamps from experiments/UI. Naive values are treated as UTC."""
    if not iso_str or not str(iso_str).strip():
        raise ValueError("empty datetime string")
    s = str(iso_str).strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def resolve_experiment_devices_and_time_range(experiment_id: str) -> Tuple[Dict[str, Any], List[str], str, str]:
    """
    Load experiment, resolve device aliases from linked groups, and compute [start, end] ISO range.
    End is 'now' for current experiments without an end time.
    """
    experiments = load_experiments()
    if experiment_id not in experiments:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    experiment = experiments[experiment_id]
    groups_map = load_groups()

    linked = experiment.get("linked_groups") or []
    devices: List[str] = []
    for gname in linked:
        g = groups_map.get(gname) or {}
        for d in g.get("devices") or []:
            if d and d not in devices:
                devices.append(d)

    if not devices:
        raise HTTPException(
            status_code=400,
            detail="This experiment has no devices: link at least one group that contains devices.",
        )

    tr = experiment.get("time_range") or {}
    start_raw = tr.get("start")
    if not start_raw:
        raise HTTPException(
            status_code=400,
            detail="Experiment has no start time; set a time range before exporting.",
        )
    start_iso = start_raw
    if experiment.get("is_current") and not tr.get("end"):
        end_iso = datetime.now(timezone.utc).isoformat()
    elif tr.get("end"):
        end_iso = tr["end"]
    else:
        raise HTTPException(
            status_code=400,
            detail="Experiment has no end time. End the experiment or set an end time before exporting.",
        )

    return experiment, devices, start_iso, end_iso


def write_raw_power_readings_csv(
    devices: List[str],
    start_iso: str,
    end_iso: str,
    out_path: Path,
    timeout_seconds: int = 600,
) -> int:
    """
    Export every stored reading in gos_rem (no time-bucketing) — one row per poll per device.
    Returns number of data rows written (excluding header).
    """
    start_dt = _parse_iso_to_utc_aware(start_iso)
    end_dt = _parse_iso_to_utc_aware(end_iso)
    if end_dt < start_dt:
        raise HTTPException(status_code=400, detail="End time is before start time.")

    conn = get_db_connection(timeout_seconds=timeout_seconds)
    row_count = 0
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT time, alias, power_watts
            FROM gos_rem
            WHERE time >= %s
              AND time <= %s
              AND alias = ANY(%s)
            ORDER BY time ASC, alias ASC
            """,
            (start_dt, end_dt, devices),
        )
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "device_alias", "power_watts"])
            while True:
                batch = cur.fetchmany(8000)
                if not batch:
                    break
                for time_val, alias, watts in batch:
                    ts_out = time_val.isoformat() if hasattr(time_val, "isoformat") else str(time_val)
                    if watts is None:
                        writer.writerow([ts_out, alias, ""])
                    else:
                        writer.writerow([ts_out, alias, float(watts)])
                    row_count += 1
        cur.close()
    finally:
        conn.close()
    return row_count


def calculate_energy_stats(data: List[Dict], devices: List[str]) -> Dict[str, float]:
    """Calculate energy statistics from data"""
    if not data or not devices:
        return {
            "total_kwh": 0.0,
            "average_watts": 0.0,
            "mean_watts": 0.0,
            "median_watts": 0.0,
            "min_watts": 0.0,
            "max_watts": 0.0
        }
    
    # Flatten all power values
    all_values = []
    for point in data:
        for device in devices:
            value = point.get(device)
            if value is not None and not (isinstance(value, float) and (value != value)):  # Check for NaN
                all_values.append(float(value))
    
    if not all_values:
        return {
            "total_kwh": 0.0,
            "average_watts": 0.0,
            "mean_watts": 0.0,
            "median_watts": 0.0,
            "min_watts": 0.0,
            "max_watts": 0.0
        }
    
    # Calculate statistics
    mean_watts = float(np.mean(all_values))
    median_watts = float(np.median(all_values))
    min_watts = float(np.min(all_values))
    max_watts = float(np.max(all_values))
    
    # Calculate total energy (kWh) - integrate power over time
    # Assuming data points are evenly spaced by interval
    if len(data) >= 2:
        time_delta = (datetime.fromisoformat(data[1]["timestamp"].replace('Z', '+00:00')) - 
                     datetime.fromisoformat(data[0]["timestamp"].replace('Z', '+00:00')))
        interval_hours = time_delta.total_seconds() / 3600.0
        
        total_watt_hours = 0.0
        for point in data:
            point_power = sum(point.get(device, 0) or 0 for device in devices)
            total_watt_hours += point_power * interval_hours
        
        total_kwh = total_watt_hours / 1000.0
    else:
        total_kwh = 0.0
    
    # Average power over the time period
    average_watts = float(np.mean(all_values))
    
    return {
        "total_kwh": total_kwh,
        "average_watts": average_watts,
        "mean_watts": mean_watts,
        "median_watts": median_watts,
        "min_watts": min_watts,
        "max_watts": max_watts
    }


# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Try to connect to database to verify service is healthy
        conn = get_db_connection()
        if conn:
            conn.close()
        return JSONResponse(content={
            "status": "healthy",
            "service": "stats-admin",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        # Even if DB fails, service is up
        return JSONResponse(content={
            "status": "healthy",
            "service": "stats-admin",
            "timestamp": datetime.now().isoformat(),
            "note": "Database connection check failed but service is running"
        }, status_code=200)

# ============================================================================
# Routes - HTML Pages
# ============================================================================

def _render_exploration(request: Request):
    """Helper function to render exploration page"""
    groups = load_groups()
    experiments = load_experiments()
    try:
        devices = get_available_devices()
    except Exception:
        devices = []
    
    # Get base URL from request for navigation links (works behind proxy)
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost:7001"))
    base_url = f"{scheme}://{host}"
    
    # Starlette >=1.0: TemplateResponse(request, name, context)
    response = templates.TemplateResponse(
        request,
        "exploration.html",
        {
            "groups": groups,
            "experiments": experiments,
            "devices": devices,
            "css_content": load_all_css(),
            "logo_data_uri": get_logo_data_uri(),
            "exploration_js": load_js_file("exploration.js"),
            "base_url": base_url,
        },
    )
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/", response_class=HTMLResponse)
async def exploration_root(request: Request):
    """Main exploration dashboard - root path (home page)"""
    return _render_exploration(request)


@app.get("/exploration", response_class=HTMLResponse)
async def exploration(request: Request):
    """Main exploration dashboard - explicit path (same as root)"""
    return _render_exploration(request)


@app.get("/manage", response_class=HTMLResponse)
async def manage_groups(request: Request):
    """Group management page"""
    groups = load_groups()
    try:
        devices = get_available_devices()
    except Exception:
        devices = []
    
    # Get base URL from request for navigation links (works behind proxy)
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost:7001"))
    base_url = f"{scheme}://{host}"
    
    response = templates.TemplateResponse(
        request,
        "index.html",
        {
            "groups": groups,
            "devices": devices,
            "css_content": load_all_css(),
            "logo_data_uri": get_logo_data_uri(),
            "script_js": load_js_file("script.js"),
            "base_url": base_url,
        },
    )
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/experiment", response_class=RedirectResponse)
async def experiment_alias():
    """Singular path → Experiments manager (common bookmark typo)."""
    return RedirectResponse(url="/experiments", status_code=307)


@app.get("/experiments", response_class=HTMLResponse)
async def manage_experiments(request: Request):
    """Experiment management page"""
    # Get base URL from request for navigation links (works behind proxy)
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost:7001"))
    base_url = f"{scheme}://{host}"
    
    response = templates.TemplateResponse(
        request,
        "experiments.html",
        {
            "css_content": load_all_css(),
            "logo_data_uri": get_logo_data_uri(),
            "base_url": base_url,
        },
    )
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Admin page for data export/import"""
    # Get base URL from request for navigation links (works behind proxy)
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost:7001"))
    base_url = f"{scheme}://{host}"
    
    response = templates.TemplateResponse(
        request,
        "admin.html",
        {
            "css_content": load_all_css(),
            "logo_data_uri": get_logo_data_uri(),
            "base_url": base_url,
        },
    )
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/gallery", response_class=HTMLResponse)
async def gallery(request: Request):
    """Snapshot gallery page"""
    snapshots = load_snapshots()
    
    # Get base URL from request for navigation links (works behind proxy)
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost:7001"))
    base_url = f"{scheme}://{host}"
    
    response = templates.TemplateResponse(
        request,
        "gallery.html",
        {
            "snapshots": snapshots,
            "css_content": load_all_css(),
            "logo_data_uri": get_logo_data_uri(),
            "gallery_js": load_js_file("gallery.js"),
            "base_url": base_url,
        },
    )
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ============================================================================
# API Endpoints - Devices & Groups
# ============================================================================

@app.get("/api/devices")
async def get_devices():
    """Get available devices"""
    try:
        devices = get_available_devices()
        return JSONResponse(content={"devices": devices})
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /api/devices endpoint: {e}")
        return JSONResponse(content={"devices": []}, status_code=200)


@app.get("/api/groups")
async def get_groups():
    """Get all groups"""
    groups = load_groups()
    return JSONResponse(content={"groups": groups})


@app.post("/api/groups")
async def create_group(
    name: str = Form(...),
    devices: str = Form(...)
):
    """Create a new device group"""
    groups = load_groups()
    
    if name in groups:
        raise HTTPException(status_code=400, detail=f"Group '{name}' already exists")
    
    device_list = [d.strip() for d in devices.split(',') if d.strip()]
    if not device_list:
        raise HTTPException(status_code=400, detail="At least one device is required")
    
    groups[name] = {
        "name": name,
        "devices": device_list,
        "created_at": datetime.now().isoformat()
    }
    
    save_groups(groups)
    
    return JSONResponse(content={"success": True, "group": groups[name]})


@app.put("/api/groups/{group_name}")
async def update_group(
    group_name: str,
    devices: str = Form(...)
):
    """Update an existing device group"""
    groups = load_groups()
    
    if group_name not in groups:
        raise HTTPException(status_code=404, detail=f"Group '{group_name}' not found")
    
    device_list = [d.strip() for d in devices.split(',') if d.strip()]
    if not device_list:
        raise HTTPException(status_code=400, detail="At least one device is required")
    
    groups[group_name]["devices"] = device_list
    groups[group_name]["updated_at"] = datetime.now().isoformat()
    
    save_groups(groups)
    
    return JSONResponse(content={"success": True, "group": groups[group_name]})


@app.delete("/api/groups/{group_name}")
async def delete_group(group_name: str):
    """Delete a device group"""
    groups = load_groups()
    
    if group_name not in groups:
        raise HTTPException(status_code=404, detail=f"Group '{group_name}' not found")
    
    del groups[group_name]
    save_groups(groups)
    
    return JSONResponse(content={"success": True})


# ============================================================================
# API Endpoints - Experiments
# ============================================================================

@app.get("/api/experiments")
async def get_experiments():
    """Get all experiments"""
    experiments = load_experiments()
    return JSONResponse(content={"experiments": experiments})


@app.post("/api/experiments")
async def create_experiment(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    start_time: Optional[str] = Form(None),
    end_time: Optional[str] = Form(None),
    is_current: Optional[str] = Form(None),  # "true" if current experiment
    linked_groups: Optional[str] = Form(None)  # Comma-separated group names
):
    """Create a new experiment with time range and linked groups"""
    experiments = load_experiments()
    
    if name in experiments:
        raise HTTPException(status_code=400, detail=f"Experiment '{name}' already exists")
    
    # Parse linked groups
    group_list = []
    if linked_groups:
        group_list = [g.strip() for g in linked_groups.split(',') if g.strip()]
    
    # Validate groups exist
    groups_data = load_groups()
    for group_name in group_list:
        if group_name not in groups_data:
            raise HTTPException(status_code=400, detail=f"Group '{group_name}' does not exist. Please create it first in Manage Groups.")
    
    # Handle current experiment
    is_current_flag = is_current and is_current.lower() == "true"
    
    # If current experiment, start_time is required but end_time can be None
    if is_current_flag:
        if not start_time:
            raise HTTPException(status_code=400, detail="Start time is required for current experiments")
        end_time = None  # Will be set when experiment ends
    else:
        # For past experiments, validate time range if both provided
        if start_time and end_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                if start_dt >= end_dt:
                    raise HTTPException(status_code=400, detail="Start time must be before end time")
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid time format: {e}")
    
    experiment_id = name.lower().replace(' ', '-').replace('_', '-')
    
    experiments[experiment_id] = {
        "id": experiment_id,
        "name": name,
        "description": description or "",
        "time_range": {
            "start": start_time or None,
            "end": end_time or None
        },
        "is_current": is_current_flag,
        "linked_groups": group_list,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    save_experiments(experiments)
    
    return JSONResponse(content={"success": True, "experiment": experiments[experiment_id]})


@app.put("/api/experiments/{experiment_id}")
async def update_experiment(
    experiment_id: str,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    start_time: Optional[str] = Form(None),
    end_time: Optional[str] = Form(None),
    linked_groups: Optional[str] = Form(None),
    is_current: Optional[bool] = Form(None)
):
    """Update an existing experiment"""
    experiments = load_experiments()
    
    if experiment_id not in experiments:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    
    experiment = experiments[experiment_id]
    
    # Update fields if provided
    if name:
        experiment["name"] = name
    if description is not None:
        experiment["description"] = description
    
    # Update time range if provided
    if start_time is not None or end_time is not None:
        if experiment.get("time_range") is None:
            experiment["time_range"] = {}
        if start_time is not None:
            experiment["time_range"]["start"] = start_time or None
        if end_time is not None:
            # If end_time is empty string, clear it (for reactivating current experiments)
            if end_time == '':
                experiment["time_range"]["end"] = None
                experiment["is_current"] = True
            else:
                experiment["time_range"]["end"] = end_time
                # If end_time is set, unset is_current
                if end_time:
                    experiment["is_current"] = False
        
        # Validate time range
        if experiment["time_range"].get("start") and experiment["time_range"].get("end"):
            try:
                start_dt = datetime.fromisoformat(experiment["time_range"]["start"].replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(experiment["time_range"]["end"].replace('Z', '+00:00'))
                if start_dt >= end_dt:
                    raise HTTPException(status_code=400, detail="Start time must be before end time")
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid time format: {e}")
    
    # Handle is_current flag explicitly if provided
    if is_current is not None:
        experiment["is_current"] = is_current
        # If setting as current, ensure end_time is cleared
        if is_current:
            if experiment.get("time_range") is None:
                experiment["time_range"] = {}
            experiment["time_range"]["end"] = None
    
    # Update linked groups if provided
    if linked_groups is not None:
        group_list = [g.strip() for g in linked_groups.split(',') if g.strip()] if linked_groups else []
        
        # Validate groups exist
        groups = load_groups()
        for group_name in group_list:
            if group_name not in groups:
                raise HTTPException(status_code=400, detail=f"Group '{group_name}' does not exist")
        
        experiment["linked_groups"] = group_list
    
    experiment["updated_at"] = datetime.now().isoformat()
    
    save_experiments(experiments)
    
    return JSONResponse(content={"success": True, "experiment": experiment})


@app.delete("/api/experiments/{experiment_id}")
async def delete_experiment(experiment_id: str):
    """Delete an experiment"""
    experiments = load_experiments()
    
    if experiment_id not in experiments:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    
    del experiments[experiment_id]
    save_experiments(experiments)
    
    return JSONResponse(content={"success": True})


@app.post("/api/experiments/{experiment_id}/start")
async def start_experiment(experiment_id: str):
    """Mark an experiment as current and set start time"""
    experiments = load_experiments()
    
    if experiment_id not in experiments:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    
    experiment = experiments[experiment_id]
    
    # Set as current and update start time to now if not set
    experiment["is_current"] = True
    if not experiment.get("time_range", {}).get("start"):
        experiment["time_range"] = experiment.get("time_range", {})
        experiment["time_range"]["start"] = datetime.now().isoformat()
    
    experiment["updated_at"] = datetime.now().isoformat()
    
    save_experiments(experiments)
    
    return JSONResponse(content={"success": True, "experiment": experiment})


@app.post("/api/experiments/{experiment_id}/end")
async def end_experiment(experiment_id: str):
    """End a current experiment by setting end time"""
    experiments = load_experiments()
    
    if experiment_id not in experiments:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    
    experiment = experiments[experiment_id]
    
    # Set end time to now and mark as not current
    experiment["is_current"] = False
    experiment["time_range"] = experiment.get("time_range", {})
    experiment["time_range"]["end"] = datetime.now().isoformat()
    
    experiment["updated_at"] = datetime.now().isoformat()
    
    save_experiments(experiments)
    
    return JSONResponse(content={"success": True, "experiment": experiment})


EXPORT_README_TEXT = """GOS REM — experiment data export
================================

power_readings.csv
  Every row is one stored measurement from TimescaleDB (collector poll), with no
  time-bucketing or averaging. Columns: timestamp, device_alias, power_watts.

experiment_metadata.json
  Experiment definition, linked groups, and export time window.

annotations.json
  Annotations recorded for this experiment (may be empty).

How this differs from charts (Exploration page)
-----------------------------------------------
The Exploration charts call /api/data/power with an aggregation interval (e.g. 1 minute).
The database aggregates with time_bucket(...) and AVG(power_watts) so the UI stays fast
for long ranges. That is NOT the same as this export: this ZIP is the full-resolution
history for the experiment time range and devices.

Gallery snapshot ZIPs embed chart data at the aggregation interval chosen when the
snapshot was saved — use this experiment export for complete raw series.

Sampling rate (not aggregation)
-------------------------------
This file is still only as granular as the **collector**: each row is one reading from
one poll cycle (one row per device per cycle). Cycles repeat every **poll interval**
(typically 30s from config / POLL_INTERVAL env). If you see about **one row per device
per minute**, the effective interval is ~60 seconds (check POLL_INTERVAL and
app/config/config.yaml poller.interval). The Exploration chart’s “1 minute” dropdown
is unrelated — that only affects the chart API’s time_bucket query, not this export.
"""


@app.get("/api/experiments/{experiment_id}/export")
async def export_experiment_full_data(experiment_id: str, background_tasks: BackgroundTasks):
    """
    Download all power readings (raw DB rows) for an experiment's time range and linked devices,
    plus metadata and annotations, as a ZIP file.
    """
    experiment, devices, start_iso, end_iso = resolve_experiment_devices_and_time_range(experiment_id)

    workdir = tempfile.mkdtemp(prefix="gos-exp-export-")
    zip_path = Path(workdir) / f"experiment-{experiment_id}-export.zip"
    try:
        csv_path = Path(workdir) / "power_readings.csv"
        row_count = write_raw_power_readings_csv(devices, start_iso, end_iso, csv_path)

        annotations_all = load_annotations()
        ann_for_exp = {
            k: v
            for k, v in annotations_all.items()
            if v.get("experiment_id") == experiment_id
        }

        meta = {
            "experiment_id": experiment_id,
            "experiment": experiment,
            "device_aliases": devices,
            "time_range": {"start": start_iso, "end": end_iso},
            "export_row_count": row_count,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(csv_path, arcname="power_readings.csv")
            zf.writestr("experiment_metadata.json", json.dumps(meta, indent=2))
            zf.writestr("annotations.json", json.dumps(ann_for_exp, indent=2))
            zf.writestr("README_export.txt", EXPORT_README_TEXT)

        safe_slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", experiment.get("name") or experiment_id)[:80]
        download_name = f"{safe_slug}_full_export.zip"

        background_tasks.add_task(shutil.rmtree, workdir, True)

        return FileResponse(
            path=str(zip_path),
            filename=download_name,
            media_type="application/zip",
        )
    except HTTPException:
        shutil.rmtree(workdir, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(workdir, ignore_errors=True)
        print(f"Error exporting experiment {experiment_id}: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


# ============================================================================
# API Endpoints - Data Queries
# ============================================================================

@app.get("/api/data/power")
async def get_power_data(
    devices: str = Query(..., description="Comma-separated list of device aliases"),
    start: str = Query(..., description="Start time (ISO format)"),
    end: str = Query(..., description="End time (ISO format)"),
    interval: str = Query("1m", description="Aggregation interval")
):
    """Get power consumption data for specified devices"""
    device_list = [d.strip() for d in devices.split(',') if d.strip()]
    
    if not device_list:
        raise HTTPException(status_code=400, detail="At least one device is required")
    
    # Validate time range and suggest better aggregation for large ranges
    try:
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
        time_range_hours = (end_dt - start_dt).total_seconds() / 3600
        
        # Auto-adjust interval for very large ranges to prevent timeouts
        # Be more aggressive with auto-adjustment based on device count and time range
        device_count = len(device_list)
        interval_seconds_map = {"10s": 10, "30s": 30, "1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "6h": 21600, "12h": 43200, "1d": 86400}
        requested_interval_seconds = interval_seconds_map.get(interval, 60)
        data_points_estimate = (time_range_hours * 3600 / requested_interval_seconds) * device_count
        
        # More aggressive auto-adjustment - force larger intervals earlier
        original_interval = interval
        if time_range_hours > 168:  # > 7 days
            if interval in ["10s", "30s", "1m", "5m", "15m", "30m"]:
                interval = "1h"
        elif time_range_hours > 72:  # > 3 days
            if interval in ["10s", "30s", "1m", "5m"]:
                interval = "15m"
            elif interval in ["15m", "30m"]:
                interval = "1h"
        elif time_range_hours > 24:  # > 1 day
            if interval in ["10s", "30s", "1m"]:
                interval = "5m"
            elif interval in ["5m"]:
                interval = "15m"
        
        # If estimated data points > 50k, force larger aggregation
        if data_points_estimate > 50000:
            if time_range_hours > 168:
                interval = "1h"
            elif time_range_hours > 72:
                interval = "1h"
            elif time_range_hours > 24:
                interval = "15m"
            else:
                interval = "5m"
        
        if interval != original_interval:
            print(f"Auto-adjusted interval from {original_interval} to {interval} for time range {time_range_hours:.1f} hours with {device_count} devices")
    except:
        pass  # If parsing fails, continue with original interval
    
    try:
        result = query_power_data(device_list, start, end, interval)
        stats = calculate_energy_stats(result["data"], result["devices"])
        
        return JSONResponse(content={
            "success": True,
            "data": result["data"],
            "devices": result["devices"],
            "stats": stats,
            "actual_interval": interval  # Return the actual interval used
        })
    except Exception as e:
        error_msg = str(e)
        print(f"Error in get_power_data: {e}")
        import traceback
        traceback.print_exc()
        
        # Check if it's a timeout-related error
        if "timeout" in error_msg.lower() or "gateway" in error_msg.lower() or "502" in error_msg or "504" in error_msg:
            # Try to get the time range info for better error message
            try:
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                time_range_hours = (end_dt - start_dt).total_seconds() / 3600
                suggested_interval = "1h" if time_range_hours > 72 else "15m" if time_range_hours > 24 else "5m"
                error_detail = f"Server timeout. Try a larger aggregation interval (e.g., {suggested_interval}) or shorter time range (currently {time_range_hours:.1f} hours)."
            except:
                error_detail = "Server timeout. Try a larger aggregation interval or shorter time range."
            raise HTTPException(status_code=502, detail=error_detail)
        else:
            raise HTTPException(status_code=500, detail=f"Failed to load data: {error_msg}")


# ============================================================================
# API Endpoints - Annotations
# ============================================================================

@app.get("/api/annotations")
async def get_annotations():
    """Get all annotations"""
    annotations = load_annotations()
    return JSONResponse(content={"annotations": annotations})


@app.post("/api/annotations")
async def create_annotation(
    experiment_id: str = Form(...),
    timestamp: str = Form(...),
    label: str = Form(...),
    description: Optional[str] = Form(""),
    color: Optional[str] = Form("#007bff")
):
    """Create a new annotation"""
    annotations = load_annotations()
    
    annotation_id = str(uuid.uuid4())
    
    annotations[annotation_id] = {
        "id": annotation_id,
        "experiment_id": experiment_id,
        "timestamp": timestamp,
        "label": label,
        "description": description or "",
        "color": color or "#007bff",
        "created_at": datetime.now().isoformat()
    }
    
    save_annotations(annotations)
    
    return JSONResponse(content={"success": True, "annotation": annotations[annotation_id]})


# ============================================================================
# API Endpoints - Snapshots
# ============================================================================

@app.get("/api/snapshots")
async def get_snapshots():
    """Get all snapshots"""
    snapshots = load_snapshots()
    return JSONResponse(content={"snapshots": snapshots})


@app.post("/api/snapshots")
async def create_snapshot(
    title: str = Form(...),
    experiment_id: str = Form(...),
    experiment_name: Optional[str] = Form(None),
    group_devices: Optional[str] = Form(None),
    start_time: str = Form(...),
    end_time: str = Form(...),
    description: Optional[str] = Form(""),
    chart_image: str = Form(...),
    energy_stats: Optional[str] = Form("{}"),
    annotations: Optional[str] = Form("[]")
):
    """Create a new snapshot"""
    snapshots = load_snapshots()
    
    snapshot_id = str(uuid.uuid4())
    
    # Parse energy stats and annotations
    try:
        stats_dict = json.loads(energy_stats) if energy_stats else {}
        annotations_list = json.loads(annotations) if annotations else []
    except:
        stats_dict = {}
        annotations_list = []
    
    # Parse group devices
    device_list = []
    if group_devices:
        device_list = [d.strip() for d in group_devices.split(',') if d.strip()]
    
    # Save image to file
    image_filename = f"{snapshot_id}.png"
    image_path = SNAPSHOTS_DIR / image_filename
    
    # Decode base64 image
    try:
        # Remove data:image/png;base64, prefix if present
        if chart_image.startswith('data:image'):
            chart_image = chart_image.split(',')[1]
        
        image_data = base64.b64decode(chart_image)
        image_path.write_bytes(image_data)
    except Exception as e:
        print(f"Error saving snapshot image: {e}")
        image_filename = None
    
    snapshots[snapshot_id] = {
        "id": snapshot_id,
        "title": title,
        "experiment_id": experiment_id,
        "experiment_name": experiment_name or experiment_id,
        "group_members": device_list,
        "time_range": {
            "start": start_time,
            "end": end_time
        },
        "description": description or "",
        "image_path": image_filename,
        "energy_stats": stats_dict,
        "annotations": annotations_list,
        "created_at": datetime.now().isoformat()
    }
    
    save_snapshots(snapshots)
    
    return JSONResponse(content={"success": True, "snapshot": snapshots[snapshot_id]})


@app.get("/api/snapshots/{snapshot_id}/image")
async def get_snapshot_image(snapshot_id: str):
    """Get snapshot image file"""
    snapshots = load_snapshots()
    
    if snapshot_id not in snapshots:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    snapshot = snapshots[snapshot_id]
    image_filename = snapshot.get("image_path")
    
    if not image_filename:
        raise HTTPException(status_code=404, detail="Snapshot image not found")
    
    image_path = SNAPSHOTS_DIR / image_filename
    
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Snapshot image file not found")
    
    return FileResponse(
        path=str(image_path),
        media_type="image/png",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@app.get("/api/snapshots/{snapshot_id}/download")
async def download_snapshot_zip(snapshot_id: str):
    """Download snapshot as ZIP file containing image and CSV data"""
    snapshots = load_snapshots()
    
    if snapshot_id not in snapshots:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    snapshot = snapshots[snapshot_id]
    
    # Create ZIP in memory
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add image file
        image_filename = snapshot.get("image_path")
        if image_filename:
            image_path = SNAPSHOTS_DIR / image_filename
            if image_path.exists():
                zip_file.write(image_path, f"{snapshot.get('title', 'snapshot').replace('/', '_')}.png")
        
        # Generate and add CSV data
        try:
            time_range = snapshot.get("time_range", {})
            devices = snapshot.get("group_members", [])
            
            start_time = time_range.get("start") if time_range else None
            end_time = time_range.get("end") if time_range else None
            
            if start_time and end_time and devices:
                # Query data from database
                data_result = query_power_data(
                    devices=devices,
                    start_time=start_time,
                    end_time=end_time,
                    interval="1m",  # Use 1 minute interval for CSV
                    timeout_seconds=60
                )
                
                # Generate CSV with raw data (use StringIO for text, then encode to bytes)
                csv_buffer = StringIO()
                if data_result.get("data"):
                    # Use devices from the query result (may differ from snapshot)
                    csv_devices = data_result.get("devices", devices)
                    fieldnames = ["timestamp"] + csv_devices
                    writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    # Write raw data - handle None values as empty strings for CSV
                    for point in data_result.get("data"):
                        row = {"timestamp": point.get("timestamp", "")}
                        for device in csv_devices:
                            value = point.get(device)
                            # Convert None to empty string, preserve numeric values
                            if value is None:
                                row[device] = ""
                            else:
                                row[device] = value
                        writer.writerow(row)
                    
                    csv_buffer.seek(0)
                    csv_filename = f"{snapshot.get('title', 'snapshot').replace('/', '_')}_data.csv"
                    csv_content = csv_buffer.getvalue()
                    csv_bytes = csv_content.encode('utf-8')
                    zip_file.writestr(csv_filename, csv_bytes)
            else:
                missing = []
                if not start_time: missing.append("start_time")
                if not end_time: missing.append("end_time")
                if not devices: missing.append("devices")
                # Still create an empty CSV with headers to indicate the issue
                csv_buffer = StringIO()
                writer = csv.DictWriter(csv_buffer, fieldnames=["timestamp", "error"])
                writer.writeheader()
                writer.writerow({"timestamp": "", "error": f"Missing required data: {', '.join(missing)}"})
                csv_buffer.seek(0)
                csv_filename = f"{snapshot.get('title', 'snapshot').replace('/', '_')}_data.csv"
                csv_content = csv_buffer.getvalue()
                csv_bytes = csv_content.encode('utf-8')
                zip_file.writestr(csv_filename, csv_bytes)
        except Exception as e:
            print(f"[CSV] Error generating CSV for snapshot {snapshot_id}: {e}")
            import traceback
            traceback.print_exc()
            # Continue even if CSV generation fails
        
        # Add metadata file (JSON)
        metadata = {
            "title": snapshot.get("title", ""),
            "experiment_id": snapshot.get("experiment_id", ""),
            "experiment_name": snapshot.get("experiment_name", ""),
            "description": snapshot.get("description", ""),
            "time_range": snapshot.get("time_range", {}),
            "created_at": snapshot.get("created_at", ""),
            "energy_stats": snapshot.get("energy_stats", {})
        }
        zip_file.writestr(
            f"{snapshot.get('title', 'snapshot').replace('/', '_')}_metadata.json",
            json.dumps(metadata, indent=2)
        )
    
    zip_buffer.seek(0)
    zip_data = zip_buffer.getvalue()
    
    # Generate filename
    safe_title = re.sub(r'[^\w\s-]', '', snapshot.get("title", "snapshot"))
    safe_title = re.sub(r'[-\s]+', '-', safe_title)
    filename = f"{safe_title}-{snapshot_id[:8]}.zip"
    
    # Use Response for in-memory content
    return Response(
        content=zip_data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
            "Cache-Control": "no-cache"
        }
    )


@app.delete("/api/snapshots/{snapshot_id}")
async def delete_snapshot(snapshot_id: str):
    """Delete a snapshot"""
    snapshots = load_snapshots()
    
    if snapshot_id not in snapshots:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    # Delete image file if exists
    snapshot = snapshots[snapshot_id]
    image_filename = snapshot.get("image_path")
    if image_filename:
        image_path = SNAPSHOTS_DIR / image_filename
        if image_path.exists():
            try:
                image_path.unlink()
            except Exception as e:
                print(f"Error deleting snapshot image: {e}")
    
    del snapshots[snapshot_id]
    save_snapshots(snapshots)
    
    return JSONResponse(content={"success": True})


# ============================================================================
# API Endpoints - Collector Control
# ============================================================================

@app.get("/api/collector/status")
async def get_collector_status():
    """Get collector status and settings"""
    if COLLECTOR_CONTROL_FILE.exists():
        try:
            with open(COLLECTOR_CONTROL_FILE, 'r') as f:
                control = json.load(f)
        except:
            control = {"enabled": True, "poll_interval": 30, "device_query_delay": 0.5}
    else:
        control = {"enabled": True, "poll_interval": 30, "device_query_delay": 0.5}
    
    # Check if collector is actually running by checking for recent data
    # If there's data in the last 2 minutes, the collector is running
    running = False
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) 
                FROM gos_rem 
                WHERE time > NOW() - INTERVAL '2 minutes'
            """)
            recent_count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            running = recent_count > 0
    except Exception as e:
        print(f"Error checking collector status from database: {e}")
        running = False
    
    return JSONResponse(content={
        "enabled": control.get("enabled", True),
        "poll_interval": control.get("poll_interval", 30),
        "device_query_delay": control.get("device_query_delay", 0.5),
        "running": running
    })


@app.post("/api/collector/control")
async def control_collector(
    enabled: Optional[bool] = Form(None),
    poll_interval: Optional[int] = Form(None),
    device_query_delay: Optional[float] = Form(None)
):
    """Control collector settings"""
    # Load current settings
    if COLLECTOR_CONTROL_FILE.exists():
        try:
            with open(COLLECTOR_CONTROL_FILE, 'r') as f:
                control = json.load(f)
        except:
            control = {"enabled": True, "poll_interval": 30, "device_query_delay": 0.5}
    else:
        control = {"enabled": True, "poll_interval": 30, "device_query_delay": 0.5}
    
    # Update settings
    if enabled is not None:
        control["enabled"] = enabled
    if poll_interval is not None:
        if poll_interval < 5 or poll_interval > 300:
            raise HTTPException(status_code=400, detail="Poll interval must be between 5 and 300 seconds")
        control["poll_interval"] = poll_interval
    if device_query_delay is not None:
        if device_query_delay < 0 or device_query_delay > 5:
            raise HTTPException(status_code=400, detail="Device query delay must be between 0 and 5 seconds")
        control["device_query_delay"] = device_query_delay
    
    # Save settings
    try:
        COLLECTOR_CONTROL_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(COLLECTOR_CONTROL_FILE, 'w') as f:
            json.dump(control, f, indent=2)
    except Exception as e:
        print(f"Error saving collector control: {e}")
        raise HTTPException(status_code=500, detail="Failed to save collector settings")
    
    # Restart collector container to apply changes
    try:
        subprocess.run(
            ["docker", "compose", "-f", "/app/docker-compose.yml", "restart", "collector"],
            timeout=10,
            capture_output=True
        )
    except Exception as e:
        print(f"Error restarting collector: {e}")
        # Don't fail the request if restart fails
    
    return JSONResponse(content={"success": True, "control": control})


# ============================================================================
# API Endpoint - Static Files (Bypass Auth)
# ============================================================================

@app.get("/api/admin/export")
async def export_database():
    """Export complete database backup as ZIP file"""
    import tempfile
    import shutil
    
    temp_dir = None
    try:
        # Create temporary directory for export files
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
        
        # 1. Export PostgreSQL database dump
        dump_file = temp_path / "database.dump"
        pg_dump_available = False
        
        try:
            # Try to use pg_dump if available
            pg_dump_cmd = [
                "pg_dump",
                f"-h{POSTGRES_HOST}",
                f"-p{POSTGRES_PORT}",
                f"-U{POSTGRES_USER}",
                f"-d{POSTGRES_DB}",
                "-Fc",  # Custom format (compressed)
                f"-f{dump_file}"
            ]
            env = os.environ.copy()
            env["PGPASSWORD"] = POSTGRES_PASSWORD
            
            result = subprocess.run(
                pg_dump_cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0 and dump_file.exists() and dump_file.stat().st_size > 0:
                pg_dump_available = True
                print("Database exported using pg_dump")
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            print(f"pg_dump not available or failed: {e}")
            pg_dump_available = False
        
        # Fallback: export data using psycopg2
        if not pg_dump_available:
            dump_file = temp_path / "database.csv"
            sql_file = temp_path / "database_schema.sql"
            try:
                print("Using custom export via psycopg2")
                conn = get_db_connection()
                try:
                    with conn.cursor() as cur:
                        # Check if table exists
                        cur.execute("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_schema = 'public' 
                                AND table_name = 'gos_rem'
                            )
                        """)
                        table_exists = cur.fetchone()[0]
                        
                        if table_exists:
                            # Export schema to SQL file
                            with open(sql_file, 'w') as f:
                                f.write("-- GOS REM Database Schema Export\n")
                                f.write("-- Generated: " + datetime.utcnow().isoformat() + "\n\n")
                                f.write("DROP TABLE IF EXISTS gos_rem CASCADE;\n\n")
                                f.write("CREATE TABLE gos_rem (\n")
                                f.write("    time TIMESTAMPTZ NOT NULL,\n")
                                f.write("    alias TEXT NOT NULL,\n")
                                f.write("    power_watts FLOAT NOT NULL\n")
                                f.write(");\n\n")
                                f.write("SELECT create_hypertable('gos_rem', 'time');\n\n")
                                f.write("-- Data will be imported from database.csv using:\n")
                                f.write("-- COPY gos_rem FROM '/path/to/database.csv' WITH CSV HEADER;\n")
                            
                            # Export data to CSV using COPY
                            with open(dump_file, 'w') as f:
                                cur.copy_expert("COPY gos_rem TO STDOUT WITH CSV HEADER", f)
                            
                            print("Database exported using custom CSV export")
                        else:
                            # Create empty files if table doesn't exist
                            with open(sql_file, 'w') as f:
                                f.write("-- No data to export\n")
                            with open(dump_file, 'w') as f:
                                f.write("time,alias,power_watts\n")
                            print("Table does not exist, created empty export files")
                finally:
                    conn.close()
            except Exception as e:
                print(f"Error in custom export: {e}")
                import traceback
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"Database export failed: {str(e)}")
        
        # 2. Copy JSON metadata files
        if GROUPS_FILE.exists():
            shutil.copy(GROUPS_FILE, temp_path / "device_groups.json")
        if EXPERIMENTS_FILE.exists():
            shutil.copy(EXPERIMENTS_FILE, temp_path / "experiments.json")
        if ANNOTATIONS_FILE.exists():
            shutil.copy(ANNOTATIONS_FILE, temp_path / "annotations.json")
        if SNAPSHOTS_FILE.exists():
            shutil.copy(SNAPSHOTS_FILE, temp_path / "snapshots.json")
        
        # 3. Copy snapshot images directory
        if SNAPSHOTS_DIR.exists():
            export_snapshots_dir = temp_path / "snapshots"
            shutil.copytree(SNAPSHOTS_DIR, export_snapshots_dir)
        
        # 4. Create manifest/metadata file
        # Determine dump file name for manifest
        dump_files_list = []
        if pg_dump_available:
            dump_files_list.append("database.dump")
        else:
            dump_files_list.extend(["database.csv", "database_schema.sql"])
        
        manifest = {
            "export_version": "1.0",
            "export_date": datetime.utcnow().isoformat(),
            "database": POSTGRES_DB,
            "export_format": "pg_dump" if pg_dump_available else "csv",
            "files": {
                "database_files": dump_files_list,
                "groups": "device_groups.json" if GROUPS_FILE.exists() else None,
                "experiments": "experiments.json" if EXPERIMENTS_FILE.exists() else None,
                "annotations": "annotations.json" if ANNOTATIONS_FILE.exists() else None,
                "snapshots_metadata": "snapshots.json" if SNAPSHOTS_FILE.exists() else None,
                "snapshots_dir": "snapshots" if SNAPSHOTS_DIR.exists() else None
            }
        }
        with open(temp_path / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # 5. Create ZIP file in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in temp_path.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(temp_path)
                    zip_file.write(file_path, arcname=str(arcname))
        
        zip_buffer.seek(0)
        
        # Generate filename
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        filename = f"gos-rem-export-{timestamp}.zip"
        
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\"",
                "Cache-Control": "no-cache"
            }
        )
        
    except Exception as e:
        print(f"Export error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
    finally:
        # Clean up temporary directory
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


@app.post("/api/admin/import")
async def import_database(file: UploadFile = File(...)):
    """Import database backup from ZIP file"""
    import tempfile
    import shutil
    
    temp_dir = None
    try:
        # Validate file type
        if not file.filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail="File must be a ZIP archive")
        
        # Create temporary directory for import files
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
        zip_path = temp_path / file.filename
        
        # Save uploaded file
        with open(zip_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        # Extract ZIP file
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            zip_file.extractall(temp_path)
        
        # Read manifest
        manifest_path = temp_path / "manifest.json"
        if not manifest_path.exists():
            raise HTTPException(status_code=400, detail="Invalid export file: manifest.json not found")
        
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        # 1. Restore database dump
        dump_file = temp_path / "database.dump"
        csv_file = temp_path / "database.csv"
        sql_file = temp_path / "database_schema.sql"
        
        try:
            if dump_file.exists():
                # Custom format dump - use pg_restore
                pg_restore_cmd = [
                    "pg_restore",
                    f"-h{POSTGRES_HOST}",
                    f"-p{POSTGRES_PORT}",
                    f"-U{POSTGRES_USER}",
                    f"-d{POSTGRES_DB}",
                    "--clean",  # Drop objects before creating
                    "--if-exists",  # Don't error if object doesn't exist
                    str(dump_file)
                ]
                env = os.environ.copy()
                env["PGPASSWORD"] = POSTGRES_PASSWORD
                
                result = subprocess.run(
                    pg_restore_cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                
                if result.returncode != 0:
                    raise Exception(f"pg_restore failed: {result.stderr}")
                    
            elif csv_file.exists() and sql_file.exists():
                # CSV export format - restore schema first, then data
                # First, restore schema
                psql_cmd = [
                    "psql",
                    f"-h{POSTGRES_HOST}",
                    f"-p{POSTGRES_PORT}",
                    f"-U{POSTGRES_USER}",
                    f"-d{POSTGRES_DB}",
                    "-f", str(sql_file)
                ]
                env = os.environ.copy()
                env["PGPASSWORD"] = POSTGRES_PASSWORD
                
                result = subprocess.run(
                    psql_cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                
                if result.returncode != 0:
                    raise Exception(f"Schema restore failed: {result.stderr}")
                
                # Then, restore data from CSV
                conn = get_db_connection()
                try:
                    with conn.cursor() as cur:
                        with open(csv_file, 'r') as f:
                            cur.copy_expert("COPY gos_rem FROM STDIN WITH CSV HEADER", f)
                    conn.commit()
                finally:
                    conn.close()
                    
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="Database restore timeout")
        except Exception as e:
            print(f"Error restoring database: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Database restore failed: {str(e)}")
        
        # 2. Restore JSON metadata files
        experiments_count = 0
        groups_count = 0
        snapshots_count = 0
        
        if (temp_path / "experiments.json").exists():
            shutil.copy(temp_path / "experiments.json", EXPERIMENTS_FILE)
            experiments = load_experiments()
            experiments_count = len(experiments)
        
        if (temp_path / "device_groups.json").exists():
            shutil.copy(temp_path / "device_groups.json", GROUPS_FILE)
            groups = load_groups()
            groups_count = len(groups)
        
        if (temp_path / "annotations.json").exists():
            shutil.copy(temp_path / "annotations.json", ANNOTATIONS_FILE)
        
        if (temp_path / "snapshots.json").exists():
            shutil.copy(temp_path / "snapshots.json", SNAPSHOTS_FILE)
            snapshots = load_snapshots()
            snapshots_count = len(snapshots)
        
        # 3. Restore snapshot images directory
        import_snapshots_dir = temp_path / "snapshots"
        if import_snapshots_dir.exists() and import_snapshots_dir.is_dir():
            # Clear existing snapshots directory and restore
            if SNAPSHOTS_DIR.exists():
                shutil.rmtree(SNAPSHOTS_DIR)
            shutil.copytree(import_snapshots_dir, SNAPSHOTS_DIR)
        
        return JSONResponse(content={
            "success": True,
            "message": "Import completed successfully",
            "experiments_count": experiments_count,
            "groups_count": groups_count,
            "snapshots_count": snapshots_count
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Import error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
    finally:
        # Clean up temporary directory
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


@app.get("/api/static/{file_path:path}")
async def serve_static_file(file_path: str):
    """Serve static files through API endpoint to bypass external auth"""
    static_file = static_dir / file_path
    
    # Security check: ensure file is within static directory
    try:
        static_file.resolve().relative_to(static_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not static_file.exists() or not static_file.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type
    media_type = "application/octet-stream"
    if file_path.endswith('.css'):
        media_type = "text/css"
    elif file_path.endswith('.js'):
        media_type = "application/javascript"
    elif file_path.endswith('.png'):
        media_type = "image/png"
    elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
        media_type = "image/jpeg"
    elif file_path.endswith('.svg'):
        media_type = "image/svg+xml"
    
    return FileResponse(
        path=str(static_file),
        media_type=media_type,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )
