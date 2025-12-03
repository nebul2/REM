# Fix Blank Dashboard Issue

## Problem
After importing the dashboard, you see a blank/empty dashboard.

## Root Cause
The dashboard JSON had a wrapper `{"dashboard": {...}}` but Grafana expects the dashboard object directly at the root level.

## Solution

### Step 1: Delete the Blank Dashboard
1. Go to Grafana: http://localhost:7003
2. Click **Dashboards** (📊 icon)
3. Find your dashboard (the blank one)
4. Click **⋮** → **Delete**

### Step 2: Import the Fixed Version
1. Click **"+"** → **"Import"**
2. Click **"Upload JSON file"**
3. Select: `grafana/dashboards/GOS_REM_Dashboard_Working.json`
4. Click **"Load"**
5. When it asks for datasource, select **"InfluxDB"**
6. Click **"Import"**

### Step 3: What You Should See
After import, you should see:
- ✅ **Device Filter dropdown** at the top (shows "All" by default)
- ✅ **Total Power (Watts)** panel
- ✅ **Power Consumption by Device** graph
- ✅ **Top Power Consumers** bar chart
- ✅ **Current Power by Device** table

## Alternative: Use the Simple Version

If the working version still has issues, try:
- File: `grafana/dashboards/GOS_REM_Dashboard_Simple.json`
- This uses `-- Grafana --` datasource placeholder (you select datasource on import)

## Still Blank?

Check:
1. **Datasource connection**: Settings → Data Sources → InfluxDB → Test
2. **Data exists**: Explore tab → Query InfluxDB manually
3. **Time range**: Make sure time range includes recent data (try "Last 1 hour")
4. **Browser console**: Check for JavaScript errors (F12)

---

**Quick Test Query** (in Explore tab):
```flux
from(bucket: "rem")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "gos_rem")
  |> filter(fn: (r) => r._field == "powerWatts")
```

This should return data if everything is working.

