# Quick Fixes for Dashboard

## Fix 1: Bar Gauge Labels (Show Device Names)

**Edit "Top Power Consumers" panel:**

1. Click panel → **Edit**
2. Go to **"Transform" tab**
3. Click **"Add transformation"**
4. Select: **"Labels to fields"**
   - Source label: `alias`
   - Keep original field name: ✅
5. **OR** add **"Organize fields"** transform:
   - Show only: `alias` and `_value`
   - Rename: `alias` → "Device", `_value` → "Power (W)"

**Alternative - Field Override:**
1. Panel → Edit → **"Field" tab**
2. **Overrides** → Add override
3. Field: `_value`
4. Property: **"Display name"** → `${__field.labels.alias}`

---

## Fix 2: Add Device Filter

**Settings → Variables → New variable:**

- **Name:** `device_filter`
- **Type:** `Query`
- **Label:** `Device Filter`
- **Data source:** `InfluxDB`
- **Query:**
```flux
import "influxdata/influxdb/schema"
schema.tagValues(bucket: "rem", tag: "alias")
```
- **Multi-value:** ✅ ON
- **Include All:** ✅ ON
- **Format:** `AsIs`
- Click **"Apply"**

This should work without JavaScript errors!

Then update panel queries to use: `|> filter(fn: (r) => r["alias"] =~ /${device_filter:regex}/)`

---

**Try Fix 1 first (Transform method) - it's the easiest!**

