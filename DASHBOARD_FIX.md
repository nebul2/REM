# Dashboard Fix Instructions

## Issue
Dashboard only shows "total data" - device filter and other panels not visible/working.

## Solution

### Step 1: Delete the old dashboard in Grafana

1. Go to Grafana: http://localhost:7003
2. Click **Dashboards** (📊 icon in left sidebar)
3. Find "GOS Remote Energy Measurement (REM)"
4. Click the **⋮** (three dots) menu → **Delete**

### Step 2: Import the fixed dashboard

1. Click **"+"** → **"Import"**
2. Click **"Upload JSON file"**
3. Select: `grafana/dashboards/GOS_REM_Dashboard_Fixed.json`
4. Click **"Load"**
5. Select datasource: **"InfluxDB"**
6. Click **"Import"**

### Step 3: Verify

After import, you should see:
- **Device Filter dropdown** at the top (with "All" selected by default)
- **Total Power Consumption** panel
- **Active Devices** count
- **Power Consumption Over Time** graph
- **Top Power Consumers** bar chart
- **Current Power by Device** table

### If the filter still doesn't show:

The device filter variable query might need manual fixing in Grafana:

1. Click the **⚙️** (gear icon) at top right → **Variables**
2. Find **"device_filter"**
3. Click **Edit**
4. Paste this query:
```flux
from(bucket: "rem")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "gos_rem")
  |> keep(columns: ["alias"])
  |> distinct(column: "alias")
  |> sort()
  |> map(fn: (r) => ({_value: r.alias}))
```
5. Click **Update**
6. Go back to dashboard

---

**Alternative: Quick Manual Fix**

If import doesn't work, create panels manually in Grafana:

1. **Add Device Filter Variable:**
   - Settings (⚙️) → Variables → New
   - Name: `device_filter`
   - Type: Query
   - Datasource: InfluxDB
   - Query: See above
   - Multi-value: ✅
   - Include All: ✅

2. **Then panels will automatically use this filter**

