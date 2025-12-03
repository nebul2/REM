# Manual Variable Fix - Step by Step

The "oe.replace is not a function" error happens when Grafana can't parse the variable query. Let's fix it manually in the UI.

## Step-by-Step Fix

### Step 1: Go to Dashboard Settings
1. Open your dashboard in Grafana
2. Click the **⚙️ Settings icon** (gear, top right corner)
3. Click **"Variables"** tab

### Step 2: Delete the Broken Variable
1. Find **"device_filter"** in the list
2. Click **"Delete"** button (trash icon)
3. Confirm deletion

### Step 3: Create New Variable (Working Version)

1. Click **"+ New variable"** button
2. Fill in these settings:

**General:**
- **Name:** `device_filter`
- **Label:** `Device Filter`
- **Type:** `Query`
- **Hide:** `No`

**Query Options:**
- **Data source:** `InfluxDB`
- **Query type:** `Flux`
- **Query:** Paste this exactly:
```flux
from(bucket: "rem")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "gos_rem")
  |> group(columns: ["alias"])
  |> distinct(column: "alias")
  |> sort()
  |> keep(columns: ["alias"])
```

**Selection Options:**
- **Multi-value:** ✅ **ON**
- **Include All option:** ✅ **ON**
- **All value:** Leave empty
- **Format:** `AsIs`

3. Click **"Apply"**

### Step 4: Test the Variable

After clicking Apply:
- The variable dropdown should appear at the top
- Click it - you should see device names loading
- If you see "No options found", the query needs adjustment

### Step 5: If Still Not Working - Try This Query

If the above doesn't work, try this simpler query:

```flux
from(bucket: "rem")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "gos_rem")
  |> group(columns: ["alias"])
  |> distinct(column: "alias")
  |> sort()
```

**OR** try using schema function:

```flux
import "influxdata/influxdb/schema"

schema.measurementTagValues(
  bucket: "rem",
  measurement: "gos_rem",
  tag: "alias"
)
```

### Step 6: Save Dashboard

1. Click **"Update"** on the variable
2. Click **"Save dashboard"** (floppy disk icon, top right)
3. Click **"Save"** in the dialog

### Step 7: Update Panel Queries

After the variable works, you need to update panel queries to use it. In each panel:

1. Click panel title → **Edit**
2. Find the query
3. Add this filter line:
```flux
|> filter(fn: (r) => contains(value: r.alias, set: ${device_filter:json}))
```

OR if using regex format:
```flux
|> filter(fn: (r) => r["alias"] =~ /${device_filter:regex}/)
```

## Alternative: Work Without Filter Variable

If the variable keeps causing issues, you can:
1. Remove the device_filter variable entirely
2. Panels will show all devices
3. Filter in Explore tab when needed

---

**Need help?** Check Grafana logs for more details:
```bash
docker-compose logs grafana | grep -i error
```

