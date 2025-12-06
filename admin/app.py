"""
GOS REM Data Exploration Tool - Complete Integrated Backend API
Combines group management and data exploration functionality
"""
from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import json
import os
import re
import uuid
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
import pandas as pd
import base64

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


def get_db_connection():
    """Get PostgreSQL/TimescaleDB connection"""
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
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
        
        query = """
        SELECT DISTINCT alias 
        FROM gos_rem 
        WHERE time >= NOW() - INTERVAL '24 hours'
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


def query_power_data(devices: List[str], start_time: str, end_time: str, interval: str = "1m") -> Dict[str, Any]:
    """Query power consumption data from TimescaleDB"""
    try:
        conn = get_db_connection()
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
        # Assuming interval is like '1m', '5m', '1h'
        interval_map = {
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
        interval_match = re.match(r'(\d+)([mhd])', interval.lower())
        if interval_match:
            num = int(interval_match.group(1))
            unit = interval_match.group(2)
            if unit == 'm':
                bucket_delta = timedelta(minutes=num)
            elif unit == 'h':
                bucket_delta = timedelta(hours=num)
            elif unit == 'd':
                bucket_delta = timedelta(days=num)
            else:
                bucket_delta = timedelta(minutes=1)
        else:
            bucket_delta = timedelta(minutes=1)
        
        # Generate all expected time buckets from start to end
        expected_timestamps = []
        current_time = start_dt
        while current_time <= end_dt:
            # Round to bucket boundary (TimescaleDB does this automatically)
            bucket_start = current_time.replace(second=0, microsecond=0)
            expected_timestamps.append(bucket_start.isoformat())
            current_time += bucket_delta
        
        # Organize existing data by timestamp
        existing_by_timestamp = {}
        for device, points in device_data.items():
            for point in points:
                ts = point["timestamp"]
                if ts not in existing_by_timestamp:
                    existing_by_timestamp[ts] = {}
                existing_by_timestamp[ts][device] = point["value"]
        
        # Create data points for ALL expected time buckets (including empty ones)
        for ts in expected_timestamps:
            point = {"timestamp": ts}
            # Add data for all devices (None if missing)
            for device in device_data.keys():
                if ts in existing_by_timestamp and device in existing_by_timestamp[ts]:
                    point[device] = existing_by_timestamp[ts][device]
                else:
                    point[device] = None
            
            # Include ALL time buckets (even if empty) so forward-fill can work
            data_points.append(point)
        
        return {
            "data": data_points,
            "devices": sorted(device_data.keys())
        }
    
    except Exception as e:
        print(f"Error querying power data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query data: {str(e)}")


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
    
    response = templates.TemplateResponse("exploration.html", {
        "request": request,
        "groups": groups,
        "experiments": experiments,
        "devices": devices,
        "css_content": load_all_css(),
        "logo_data_uri": get_logo_data_uri(),
        "exploration_js": load_js_file("exploration.js"),
        "base_url": base_url
    })
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
    
    response = templates.TemplateResponse("index.html", {
        "request": request,
        "groups": groups,
        "devices": devices,
        "css_content": load_all_css(),
        "logo_data_uri": get_logo_data_uri(),
        "script_js": load_js_file("script.js"),
        "base_url": base_url
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/experiments", response_class=HTMLResponse)
async def manage_experiments(request: Request):
    """Experiment management page"""
    # Get base URL from request for navigation links (works behind proxy)
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost:7001"))
    base_url = f"{scheme}://{host}"
    
    response = templates.TemplateResponse("experiments.html", {
        "request": request,
        "css_content": load_all_css(),
        "logo_data_uri": get_logo_data_uri(),
        "base_url": base_url
    })
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
    
    response = templates.TemplateResponse("gallery.html", {
        "request": request,
        "snapshots": snapshots,
        "css_content": load_all_css(),
        "logo_data_uri": get_logo_data_uri(),
        "gallery_js": load_js_file("gallery.js"),
        "base_url": base_url
    })
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


@app.get("/api/groups/grafana")
async def get_groups_for_grafana():
    """API endpoint formatted for Grafana variable queries"""
    groups = load_groups()
    
    grafana_format = []
    grafana_format.append({"text": "All Devices", "value": ".*"})
    
    for group_name, group_data in groups.items():
        device_regex = "|".join([f"^{re.escape(device)}$" for device in group_data.get("devices", [])])
        if device_regex:
            grafana_format.append({
                "text": group_data.get("name", group_name),
                "value": device_regex
            })
    
    return JSONResponse(content=grafana_format)


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
    
    # Also save as experiment
    experiments = load_experiments()
    experiments[name] = {
        "name": name,
        "devices": device_list,
        "created_at": datetime.now().isoformat()
    }
    save_experiments(experiments)
    
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
    
    # Also update experiment
    experiments = load_experiments()
    if group_name in experiments:
        experiments[group_name]["devices"] = device_list
        experiments[group_name]["updated_at"] = datetime.now().isoformat()
        save_experiments(experiments)
    
    return JSONResponse(content={"success": True, "group": groups[group_name]})


@app.delete("/api/groups/{group_name}")
async def delete_group(group_name: str):
    """Delete a device group"""
    groups = load_groups()
    
    if group_name not in groups:
        raise HTTPException(status_code=404, detail=f"Group '{group_name}' not found")
    
    del groups[group_name]
    save_groups(groups)
    
    # Also delete from experiments
    experiments = load_experiments()
    if group_name in experiments:
        del experiments[group_name]
        save_experiments(experiments)
    
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
    linked_groups: Optional[str] = Form(None)
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
            experiment["time_range"]["end"] = end_time or None
        
        # Validate time range
        if experiment["time_range"].get("start") and experiment["time_range"].get("end"):
            try:
                start_dt = datetime.fromisoformat(experiment["time_range"]["start"].replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(experiment["time_range"]["end"].replace('Z', '+00:00'))
                if start_dt >= end_dt:
                    raise HTTPException(status_code=400, detail="Start time must be before end time")
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid time format: {e}")
    
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
    
    try:
        result = query_power_data(device_list, start, end, interval)
        stats = calculate_energy_stats(result["data"], result["devices"])
        
        return JSONResponse(content={
            "success": True,
            "data": result["data"],
            "devices": result["devices"],
            "stats": stats
        })
    except Exception as e:
        print(f"Error in get_power_data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
            control = {"enabled": True, "poll_interval": 30}
    else:
        control = {"enabled": True, "poll_interval": 30}
    
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
        "running": running
    })


@app.post("/api/collector/control")
async def control_collector(
    enabled: Optional[bool] = Form(None),
    poll_interval: Optional[int] = Form(None)
):
    """Control collector settings"""
    # Load current settings
    if COLLECTOR_CONTROL_FILE.exists():
        try:
            with open(COLLECTOR_CONTROL_FILE, 'r') as f:
                control = json.load(f)
        except:
            control = {"enabled": True, "poll_interval": 30}
    else:
        control = {"enabled": True, "poll_interval": 30}
    
    # Update settings
    if enabled is not None:
        control["enabled"] = enabled
    if poll_interval is not None:
        if poll_interval < 5 or poll_interval > 300:
            raise HTTPException(status_code=400, detail="Poll interval must be between 5 and 300 seconds")
        control["poll_interval"] = poll_interval
    
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
