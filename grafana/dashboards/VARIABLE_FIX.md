# Fix "oe.replace is not a function" Error

## Problem
Grafana shows error: `Templating [device_filter] Error updating options: oe.replace is not a function`

## Cause
The variable query format is incorrect. Grafana's Flux variable queries need to return data in a specific format.

## Fix

### Option 1: Edit Variable Manually (Recommended)

1. Go to your dashboard
2. Click **⚙️ Settings** (gear icon, top right)
3. Click **"Variables"** tab
4. Find **"device_filter"** variable
5. Click **Edit**

6. **Change the Query to:**
```flux
import "influxdata/influxdb/schema"

schema.measurementTagValues(
  bucket: "rem",
  measurement: "gos_rem",
  tag: "alias"
)
```

OR use this simpler version:

```flux
from(bucket: "rem")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "gos_rem")
  |> keep(columns: ["alias"])
  |> distinct(column: "alias")
  |> sort()
```

7. **Make sure:**
   - Multi-value: ✅ ON
   - Include All option: ✅ ON
   - Format: AsIs
   
8. Click **"Update"**
9. Click **"Save dashboard"**

### Option 2: Use Label Query

If the above doesn't work, try this query:

```flux
import "influxdata/influxdb/schema"

schema.tagValues(bucket: "rem", tag: "alias")
```

### Option 3: Simplest Query

If still having issues, use this very simple query:

```flux
from(bucket: "rem")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "gos_rem")
  |> group()
  |> distinct(column: "alias")
  |> sort()
```

Then in the panel queries, you might need to adjust how the filter is used.

## Why This Happens

Grafana expects variable queries to return a column named `_value`. When using Flux with InfluxDB, the query needs to be formatted in a way that Grafana can parse.

The `schema.tagValues()` or `schema.measurementTagValues()` functions are the recommended way for getting tag values in Grafana variables.

## After Fix

Once the variable query works:
1. The dropdown should populate with device names
2. You should be able to select devices
3. Panels should filter based on selection

