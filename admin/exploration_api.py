"""
GOS REM Data Exploration API
Enhanced API endpoints for data exploration, experiments, annotations, and snapshots
"""
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from influxdb_client import InfluxDBClient
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import re

# Import existing functions
from app import (
    DATA_DIR, INFLUXDB_URL, INFLUXDB_ORG, 
    INFLUXDB_BUCKET, INFLUXDB_TOKEN,
    load_groups
)

# Data files
EXPERIMENTS_FILE = DATA_DIR / "experiments.json"
ANNOTATIONS_FILE = DATA_DIR / "annotations.json"
SNAPSHOTS_FILE = DATA_DIR / "snapshots.json"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"

# Ensure directories exist
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
EXPERIMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Experiment Management
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


# ============================================================================
# InfluxDB Data Queries
# ============================================================================

def query_power_data(devices: List[str], start_time: str, end_time: str, interval: str = "1m") -> Dict[str, Any]:
    """
    Query power consumption data from InfluxDB
    
    Returns:
        {
            "data": [
                {"timestamp": "...", "device1": 100, "device2": 200, ...},
                ...
            ],
            "devices": ["device1", "device2", ...]
        }
    """
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()
        
        # Build device filter regex
        device_filter = "|".join([f"^{re.escape(d)}$" for d in devices]) if devices else ".*"
        
        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: {start_time}, stop: {end_time})
          |> filter(fn: (r) => r._measurement == "gos_rem")
          |> filter(fn: (r) => r._field == "powerWatts")
          |> filter(fn: (r) => r["alias"] =~ /{device_filter}/)
          |> aggregateWindow(every: {interval}, fn: mean, createEmpty: false)
          |> pivot(rowKey:["_time"], columnKey: ["alias"], valueColumn: "_value")
        '''
        
        result = query_api.query(query)
        
        # Convert to structured data
        data_points = []
        columns = set()
        
        for table in result:
            for record in table.records:
                timestamp = record.get_time().isoformat()
                point = {"timestamp": timestamp}
                
                for key, value in record.values.items():
                    if key not in ["_time", "_start", "_stop", "result", "table"] and value is not None:
                        if isinstance(value, (int, float)):
                            point[key] = float(value)
                            columns.add(key)
                
                if len(point) > 1:  # Has data beyond timestamp
                    data_points.append(point)
        
        client.close()
        
        # Sort by timestamp
        data_points.sort(key=lambda x: x["timestamp"])
        
        return {
            "data": data_points,
            "devices": sorted(columns)
        }
    
    except Exception as e:
        print(f"Error querying power data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query data: {e}")


def calculate_energy_stats(data: List[Dict], devices: List[str], start_time: str, end_time: str) -> Dict[str, Any]:
    """
    Calculate energy statistics from power data
    
    Returns:
        {
            "total_kwh": float,
            "average_watts": float,
            "mean_watts": float,
            "median_watts": float,
            "min_watts": float,
            "max_watts": float,
            "per_device": {
                "device1": {"total_kwh": ..., "avg_watts": ...},
                ...
            }
        }
    """
    if not data:
        return {
            "total_kwh": 0.0,
            "average_watts": 0.0,
            "mean_watts": 0.0,
            "median_watts": 0.0,
            "min_watts": 0.0,
            "max_watts": 0.0,
            "per_device": {}
        }
    
    # Convert to DataFrame for easier calculations
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    
    # Calculate time delta in hours
    if len(df) > 1:
        time_delta_hours = (df.index[-1] - df.index[0]).total_seconds() / 3600
    else:
        time_delta_hours = 0.001  # Minimum 1ms
    
    # Calculate per-device statistics
    per_device = {}
    all_values = []
    
    for device in devices:
        if device in df.columns:
            values = df[device].dropna()
            if len(values) > 0:
                # Convert power (W) to energy (kWh)
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
    
    # Aggregate statistics
    if all_values:
        total_power = sum([df[dev].sum() * (time_delta_hours / len(df)) for dev in devices if dev in df.columns]) / 1000
        total_kwh = total_power / len(devices) if devices else 0
        
        return {
            "total_kwh": float(total_kwh),
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


# ============================================================================
# Annotations Management
# ============================================================================

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


# ============================================================================
# Snapshots Management
# ============================================================================

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

