# Fix Device Filter - Step by Step (5 minutes)

## The Problem
Device filter dropdown only shows "All" - no device names appear.

## Solution: Manual Fix in Grafana UI

### Step 1: Open Variable Settings
1. In your dashboard, click **⚙️ Settings** (gear icon, top right)
2. Click **"Variables"** tab
3. Find **"device_filter"** in the list
4. Click **"Edit"**

### Step 2: Fix the Query

**Delete the current query and paste this EXACT query:**

```flux
from(bucket: "rem")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "gos_rem")
  |> keep(columns: ["alias"])
  |> distinct(column: "alias")
  |> sort()
```

### Step 3: Check These Settings

1. **Data source:** Should be "InfluxDB" (or "-- Grafana --")
2. **Query type:** Should be "Flux"
3. **Refresh:** Try **"On Time Range Change"** (not "On Dashboard Load")
4. **Multi-value:** ✅ **ON**
5. **Include All option:** ✅ **ON**
6. **Format:** Leave as default or try **"Text"**

### Step 4: Test

1. Click **"Test query"** button (if available)
   - Should show list of device names
   - If it shows data, continue
   - If "No data", check datasource connection

2. Click **"Apply"**

3. Click **"Save dashboard"** (floppy disk icon, top right)

### Step 5: Check Dropdown

1. Close settings (click X)
2. Look at the dashboard
3. Click the **"Device Filter"** dropdown
4. **Should now show all device names!**

---

## Alternative: If Query Still Doesn't Work

Try this even simpler query:

```flux
from(bucket: "rem")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "gos_rem")
  |> group(columns: ["alias"])
  |> distinct(column: "alias")
  |> sort()
```

OR try using the schema function:

```flux
import "influxdata/influxdb/schema"

schema.tagValues(bucket: "rem", tag: "alias")
```

---

## If Still Not Working

1. **Check Data Source:**
   - Settings → Data Sources → InfluxDB
   - Click "Test" button
   - Should show "Data source is working"

2. **Check Time Range:**
   - Make sure there's data in the last 24 hours
   - Try expanding to -7d (7 days)

3. **Check Variable Format:**
   - In variable settings, try different "Format" options
   - Try "Text", "Single quote", etc.

---

**This manual fix should work - Grafana variable queries are sometimes finicky when imported from JSON but work fine when edited in the UI!**

