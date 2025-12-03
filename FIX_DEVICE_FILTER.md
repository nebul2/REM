# Fix Device Filter - Only Shows "All"

## Problem
Device filter dropdown only shows "All" - no device names appear.

## Quick Fix in Grafana

1. **Go to Dashboard Settings**
   - Click ⚙️ Settings (gear icon, top right)
   - Click "Variables" tab

2. **Edit device_filter Variable**
   - Find "device_filter" in the list
   - Click "Edit"

3. **Change the Query**
   Replace the query with this simpler version:

```flux
from(bucket: "rem")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "gos_rem")
  |> keep(columns: ["alias"])
  |> distinct(column: "alias")
  |> sort()
```

4. **Check Settings**
   - Multi-value: ✅ ON
   - Include All option: ✅ ON
   - Format: `AsIs` or leave default
   - Refresh: `On Dashboard Load`

5. **Test**
   - Click "Apply"
   - Click dropdown - should see device names
   - If still not working, try "Test query" button first

## Alternative Query (If First Doesn't Work)

Try this even simpler version:

```flux
from(bucket: "rem")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "gos_rem")
  |> group(columns: ["alias"])
  |> distinct(column: "alias")
  |> sort()
```

## Troubleshooting

If still only showing "All":

1. **Check Data Source**
   - Verify "InfluxDB" datasource is working
   - Settings → Data Sources → InfluxDB → Test

2. **Check Time Range**
   - Try expanding time range in query to `-24h` or `-7d`
   - Make sure data exists in that range

3. **Test Query Directly**
   - Go to Explore tab
   - Paste the query above
   - Should return list of device names
   - If it works there but not in variable, it's a Grafana variable parsing issue

4. **Check Variable Format**
   - Format should be: `AsIs`, `Single quote`, or default
   - NOT: `JSON`, `CSV`, etc.

## Updated Dashboard

I've updated `GOS_REM_Dashboard_Working.json` with the simpler query. Re-import if needed.

