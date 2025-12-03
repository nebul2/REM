"""
GOS REM Data Exploration Tool - Complete Backend API
Enhanced app.py with all exploration endpoints integrated
"""
from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import os
import re
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
import numpy as np
import pandas as pd
import base64

# Import existing group management
from app import (
    DATA_DIR, GROUPS_FILE, INFLUXDB_URL, INFLUXDB_ORG,
    INFLUXDB_BUCKET, INFLUXDB_TOKEN,
    load_groups, save_groups, get_available_devices
)

app = FastAPI(title="GOS REM Data Exploration Tool")

# Templates and static files
templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"
templates = Jinja2Templates(directory=str(templates_dir))
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Data files
EXPERIMENTS_FILE = DATA_DIR / "experiments.json"
ANNOTATIONS_FILE = DATA_DIR / "annotations.json"
SNAPSHOTS_FILE = DATA_DIR / "snapshots.json"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Helper Functions
# ============================================================================

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
        with open(EXPERIMENTS_FILE, 'w') as f:
            json.dump(experiments, f, indent=2)
    except Exception as e:
        print(f"Error saving experiments: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save experiments: {e}")


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
        with open(ANNOTATIONS_FILE, 'w') as f:
            json.dump(annotations, f, indent=2)
    except Exception as e:
        print(f"Error saving annotations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save annotations: {e}")


def load_snapshots() -> dict:
    """Load snapshots metadata from JSON file"""
    if SNAPSHOTS_FILE.exists():
        try:
            with open(SNAPSHOTS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading snapshots: {e}")
            return {}
    return {}


def save_snapshots(snapshots: dict):
    """Save snapshots metadata to JSON file"""
    try:
        with open(SNAPSHOTS_FILE, 'w') as f:
            json.dump(snapshots, f, indent=2)
    except Exception as e:
        print(f"Error saving snapshots: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save snapshots: {e}")


def query_power_data(devices: List[str], start_time: str, end_time: str, interval: str = "1m") -> Dict[str, Any]:
    """Query power consumption data from InfluxDB"""
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()
        
        device_filter = "|".join([f"^{re.escape(d)}$" for d in devices]) if devices else ".*"
        
        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: {start_time}, stop: {end_time})
          |> filter(fn: (r) => r._measurement == "gos_rem")
          |> filter(fn: (r) => r._field == "powerWatts")
          |> filter(fn: (r) => r["alias"] =~ /{device_filter}/)
          |> aggregateWindow(every: {interval}, fn: mean, createEmpty: false)
        '''
        
        result = query_api.query(query)
        data_points = []
        device_data = {}
        
        for table in result:
            for record in table.records:
                timestamp = record.get_time().isoformat()
                alias = record.values.get("alias")
                value = record.values.get("_value")
                
                if alias and value is not None:
                    if alias not in device_data:
                        device_data[alias] = []
                    device_data[alias].append({"timestamp": timestamp, "value": float(value)})
        
        client.close()
        
        # Organize by timestamp
        all_timestamps = set()
        for device, points in device_data.items():
            all_timestamps.update([p["timestamp"] for p in points])
        
        all_timestamps = sorted(all_timestamps)
        
        for ts in all_timestamps:
            point = {"timestamp": ts}
            for device in device_data.keys():
                device_points = device_data[device]
                matching = [p for p in device_points if p["timestamp"] == ts]
                point[device] = matching[0]["value"] if matching else None
            
            if len([v for v in point.values() if v is not None]) > 1:
                data_points.append(point)
        
        return {
            "data": data_points,
            "devices": sorted(device_data.keys())
        }
    
    except Exception as e:
        print(f"Error querying power data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query data: {str(e)}")


def calculate_energy_stats(data: List[Dict], devices: List[str]) -> Dict[str, Any]:
    """Calculate energy statistics from power data"""
    if not data or not devices:
        return {
            "total_kwh": 0.0,
            "average_watts": 0.0,
            "mean_watts": 0.0,
            "median_watts": 0.0,
            "min_watts": 0.0,
            "max_watts": 0.0,
            "per_device": {}
        }
    
    try:
        df = pd.DataFrame(data)
        if df.empty or 'timestamp' not in df.columns:
            return {
                "total_kwh": 0.0,
                "average_watts": 0.0,
                "mean_watts": 0.0,
                "median_watts": 0.0,
                "min_watts": 0.0,
                "max_watts": 0.0,
                "per_device": {}
            }
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
        
        time_delta_hours = (df.index[-1] - df.index[0]).total_seconds() / 3600 if len(df) > 1 else 0.001
        
        per_device = {}
        all_values = []
        
        for device in devices:
            if device in df.columns:
                values = df[device].dropna()
                if len(values) > 0:
                    avg_watts = values.mean()
                    total_kwh = (avg_watts * time_delta_hours) / 1000
                    
                    per_device[device] = {
                        "total_kwh": float(total_kwh),
                        "avg_watts": float(avg_watts),
                        "mean_watts": float(values.mean()),
                        "median_watts": float(values.median()),
                        "min_watts": float(values.min()),
                        "max_watts": float(values.max())
                    }
                    
                    all_values.extend(values.tolist())
        
        if all_values:
            total_kwh_sum = sum([per_device[dev]["total_kwh"] for dev in devices if dev in per_device])
            
            return {
                "total_kwh": float(total_kwh_sum),
                "average_watts": float(np.mean(all_values)),
                "mean_watts": float(np.mean(all_values)),
                "median_watts": float(np.median(all_values)),
                "min_watts": float(np.min(all_values)),
                "max_watts": float(np.max(all_values)),
                "per_device": per_device
            }
        else:
            return {
                "total_kwh": 0.0,
                "average_watts": 0.0,
                "mean_watts": 0.0,
                "median_watts": 0.0,
                "min_watts": 0.0,
                "max_watts": 0.0,
                "per_device": {}
            }
    except Exception as e:
        print(f"Error calculating energy stats: {e}")
        return {
            "total_kwh": 0.0,
            "average_watts": 0.0,
            "mean_watts": 0.0,
            "median_watts": 0.0,
            "min_watts": 0.0,
            "max_watts": 0.0,
            "per_device": {}
        }


# ============================================================================
# Routes - Main Pages
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def exploration(request: Request):
    """Main exploration dashboard"""
    groups = load_groups()
    experiments = load_experiments()
    devices = get_available_devices()
    
    return templates.TemplateResponse("exploration.html", {
        "request": request,
        "groups": groups,
        "experiments": experiments,
        "devices": devices
    })


@app.get("/manage", response_class=HTMLResponse)
async def manage_groups(request: Request):
    """Group management page (existing functionality)"""
    groups = load_groups()
    devices = get_available_devices()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "groups": groups,
        "devices": devices
    })


@app.get("/gallery", response_class=HTMLResponse)
async def gallery(request: Request):
    """Snapshot gallery page"""
    snapshots = load_snapshots()
    
    return templates.TemplateResponse("gallery.html", {
        "request": request,
        "snapshots": snapshots
    })


# ============================================================================
# API Endpoints - Data Queries
# ============================================================================

@app.get("/api/data/power")
async def get_power_data(
    devices: str = Query(..., description="Comma-separated device list"),
    start: str = Query(..., description="Start time (ISO format)"),
    end: str = Query(..., description="End time (ISO format)"),
    interval: str = Query("1m", description="Aggregation interval")
):
    """Get power consumption data for specified devices and time range"""
    device_list = [d.strip() for d in devices.split(",") if d.strip()]
    
    try:
        data_result = query_power_data(device_list, start, end, interval)
        
        # Calculate statistics
        stats = calculate_energy_stats(data_result["data"], data_result["devices"])
        
        return JSONResponse(content={
            "success": True,
            "data": data_result["data"],
            "devices": data_result["devices"],
            "stats": stats
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API Endpoints - Experiments (using groups as experiments)
# ============================================================================

@app.get("/api/experiments")
async def get_experiments():
    """Get all experiments (groups)"""
    groups = load_groups()
    return JSONResponse(content={"experiments": groups})


@app.post("/api/experiments")
async def create_experiment(
    name: str = Form(...),
    devices: str = Form(...),
    description: str = Form("")
):
    """Create a new experiment (group)"""
    device_list = [d.strip() for d in devices.split(",") if d.strip()]
    if not device_list:
        raise HTTPException(status_code=400, detail="At least one device must be selected")
    
    groups = load_groups()
    
    if name in groups:
        raise HTTPException(status_code=400, detail=f"Experiment '{name}' already exists")
    
    now = datetime.now().isoformat()
    groups[name] = {
        "name": name,
        "devices": device_list,
        "description": description,
        "created_at": now,
        "updated_at": now
    }
    
    save_groups(groups)
    return JSONResponse(content={"success": True, "experiment": groups[name]})


# ============================================================================
# API Endpoints - Annotations
# ============================================================================

@app.get("/api/annotations")
async def get_annotations(experiment: Optional[str] = None):
    """Get annotations, optionally filtered by experiment"""
    annotations = load_annotations()
    
    if experiment:
        filtered = {k: v for k, v in annotations.items() if v.get("experiment_id") == experiment}
        return JSONResponse(content={"annotations": filtered})
    
    return JSONResponse(content={"annotations": annotations})


@app.post("/api/annotations")
async def create_annotation(
    experiment_id: str = Form(...),
    timestamp: str = Form(...),
    label: str = Form(...),
    description: str = Form(""),
    color: str = Form("#007bff")
):
    """Create a new annotation"""
    annotations = load_annotations()
    
    annotation_id = str(uuid.uuid4())
    annotations[annotation_id] = {
        "id": annotation_id,
        "experiment_id": experiment_id,
        "timestamp": timestamp,
        "label": label,
        "description": description,
        "color": color,
        "created_at": datetime.now().isoformat()
    }
    
    save_annotations(annotations)
    return JSONResponse(content={"success": True, "annotation": annotations[annotation_id]})


@app.delete("/api/annotations/{annotation_id}")
async def delete_annotation(annotation_id: str):
    """Delete an annotation"""
    annotations = load_annotations()
    
    if annotation_id not in annotations:
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    del annotations[annotation_id]
    save_annotations(annotations)
    return JSONResponse(content={"success": True})


# ============================================================================
# API Endpoints - Snapshots
# ============================================================================

@app.get("/api/snapshots")
async def get_snapshots(
    experiment: Optional[str] = None,
    search: Optional[str] = None
):
    """Get all snapshots, optionally filtered"""
    snapshots = load_snapshots()
    
    if experiment:
        filtered = {k: v for k, v in snapshots.items() if v.get("experiment_id") == experiment}
        return JSONResponse(content={"snapshots": filtered})
    
    if search:
        filtered = {
            k: v for k, v in snapshots.items()
            if search.lower() in v.get("title", "").lower() or
            search.lower() in v.get("description", "").lower()
        }
        return JSONResponse(content={"snapshots": filtered})
    
    return JSONResponse(content={"snapshots": snapshots})


@app.post("/api/snapshots")
async def create_snapshot(
    title: str = Form(...),
    experiment_id: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    description: str = Form(""),
    chart_image: str = Form(""),  # Base64 encoded image
    energy_stats: str = Form("{}"),  # JSON string
    annotations: str = Form("[]")  # JSON string
):
    """Create a new snapshot"""
    snapshots = load_snapshots()
    
    snapshot_id = str(uuid.uuid4())
    
    # Save image if provided
    image_path = None
    if chart_image:
        image_path = SNAPSHOTS_DIR / f"{snapshot_id}.png"
        try:
            image_data = base64.b64decode(chart_image.split(',')[1])
            with open(image_path, 'wb') as f:
                f.write(image_data)
            image_path = f"snapshots/{snapshot_id}.png"
        except Exception as e:
            print(f"Error saving snapshot image: {e}")
    
    try:
        stats_dict = json.loads(energy_stats)
        annotations_list = json.loads(annotations)
    except:
        stats_dict = {}
        annotations_list = []
    
    snapshots[snapshot_id] = {
        "id": snapshot_id,
        "title": title,
        "description": description,
        "experiment_id": experiment_id,
        "time_range": {
            "start": start_time,
            "end": end_time
        },
        "energy_stats": stats_dict,
        "annotations": annotations_list,
        "image_path": image_path,
        "created_at": datetime.now().isoformat()
    }
    
    save_snapshots(snapshots)
    return JSONResponse(content={"success": True, "snapshot": snapshots[snapshot_id]})


@app.delete("/api/snapshots/{snapshot_id}")
async def delete_snapshot(snapshot_id: str):
    """Delete a snapshot"""
    snapshots = load_snapshots()
    
    if snapshot_id not in snapshots:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    # Delete image file
    snapshot = snapshots[snapshot_id]
    if snapshot.get("image_path"):
        image_file = DATA_DIR / snapshot["image_path"]
        if image_file.exists():
            image_file.unlink()
    
    del snapshots[snapshot_id]
    save_snapshots(snapshots)
    return JSONResponse(content={"success": True})


# ============================================================================
# Keep existing group endpoints for compatibility
# ============================================================================

@app.get("/api/devices")
async def get_devices():
    """Get available devices"""
    devices = get_available_devices()
    return JSONResponse(content={"devices": devices})


@app.get("/api/groups")
async def get_groups():
    """Get all groups"""
    groups = load_groups()
    return JSONResponse(content={"groups": groups})


@app.post("/api/groups")
async def create_group(name: str = Form(...), devices: str = Form(...)):
    """Create a group"""
    device_list = [d.strip() for d in devices.split(",") if d.strip()]
    if not device_list:
        raise HTTPException(status_code=400, detail="At least one device must be selected")
    
    groups = load_groups()
    if name in groups:
        raise HTTPException(status_code=400, detail=f"Group '{name}' already exists")
    
    now = datetime.now().isoformat()
    groups[name] = {
        "name": name,
        "devices": device_list,
        "created_at": now,
        "updated_at": now
    }
    
    save_groups(groups)
    return JSONResponse(content={"success": True, "group": groups[name]})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7001)

