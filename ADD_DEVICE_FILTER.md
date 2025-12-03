# Add Device Filter - Step by Step

## Goal
Add a working device filter dropdown that doesn't cause JavaScript errors.

## Method: Use Text Variable with Manual Options

This avoids the query variable JavaScript errors.

### Step 1: Create Device List Variable

1. **Dashboard Settings** → **Variables** tab
2. Click **"+ New variable"**

**Configuration:**
- **Name:** `device_filter`
- **Type:** `Query` (yes, query - but simpler)
- **Label:** `Device Filter`
- **Data source:** `InfluxDB`
- **Refresh:** `On Dashboard Load`
- **Query type:** `Flux`

**Query (use this exact one):**
```flux
from(bucket: "rem")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "gos_rem")
  |> keep(columns: ["alias"])
  |> distinct(column: "alias")
  |> sort()
```

**OR try schema function:**
```flux
import "influxdata/influxdb/schema"
schema.tagValues(bucket: "rem", tag: "alias")
```

**Selection Options:**
- **Multi-value:** ✅ ON
- **Include All option:** ✅ ON
- **All value:** Leave empty or use `.*`
- **Format:** `AsIs` or `Text`

3. Click **"Apply"**
4. Test - dropdown should populate

### Step 2: Update Panel Queries

If the variable works, update panels to use it:

**In panel queries, add filter:**
```flux
|> filter(fn: (r) => r["alias"] =~ /${device_filter:regex}/)
```

### Alternative: Manual Text Variable (Simpler)

If query variable still fails:

1. Create variable:
   - **Type:** `Text`
   - **Name:** `device_filter`
   - **Label:** `Device Filter`
   - **Default value:** `.*` (shows all)
   - **Multi-value:** ✅ ON

2. Use in queries:
```flux
|> filter(fn: (r) => r["alias"] =~ /${device_filter:regex}/)
```

3. Manually type device names in filter (not ideal but works)

---

**Try the schema.tagValues() query first - it's simpler and might avoid the JavaScript errors.**

