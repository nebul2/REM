# Quick Dashboard Fix

## Problem
You only see "total data" - no device filter dropdown or other panels visible.

## Quick Fix (2 minutes)

### Option 1: Re-import the fixed dashboard

1. **Delete old dashboard**:
   - Grafana → Dashboards → Find "GOS Remote Energy Measurement (REM)"
   - Click ⋮ → Delete

2. **Import fixed version**:
   - Click "+" → Import
   - Upload: `grafana/dashboards/GOS_REM_Dashboard_Fixed.json`
   - Select datasource: "InfluxDB"
   - Click Import

### Option 2: Fix the device filter manually

If the filter still doesn't show, add it manually:

1. **Go to Dashboard Settings**:
   - Open your dashboard
   - Click ⚙️ (gear icon, top right)
   - Click "Variables" tab

2. **Add Device Filter**:
   - Click "New variable"
   - Name: `device_filter`
   - Type: **Query**
   - Label: **Device Filter**
   - Datasource: **InfluxDB**
   - Query:
   ```flux
   from(bucket: "rem")
     |> range(start: -1h)
     |> filter(fn: (r) => r._measurement == "gos_rem")
     |> keep(columns: ["alias"])
     |> distinct(column: "alias")
     |> sort()
     |> map(fn: (r) => ({_value: r.alias}))
   ```
   - Multi-value: ✅ **ON**
   - Include All option: ✅ **ON**
   - Click "Apply"

3. **Now the filter dropdown should appear at the top!**

4. **Update panel queries** to use the filter (if needed):
   - In any panel, edit the query
   - Add filter: `|> filter(fn: (r) => contains(value: r.alias, set: ${device_filter:json}))`
   - Or use: `|> filter(fn: (r) => r.alias =~ /${device_filter:pipe}/)`

## What You Should See After Fix

✅ **Device Filter dropdown** at the top (shows all 34 devices)
✅ **Total Power Consumption** panel (big number)
✅ **Active Devices** count
✅ **Power Consumption Over Time** graph (time series)
✅ **Top Power Consumers** bar chart
✅ **Current Power by Device** table

## Still Not Working?

Check:
1. InfluxDB datasource is working: Settings → Data Sources → InfluxDB → Test
2. Data exists: Explore tab → Query InfluxDB → Should see data
3. Browser refresh: Hard refresh (Cmd+Shift+R / Ctrl+Shift+R)

---

**Need help?** The device filter variable is the key - once that's working, everything else will work!

