# Final Dashboard Fixes

## Changes Made

1. ✅ **Removed "Current Power by Device" panel** - completely deleted
2. ✅ **Made "Top Power Consumers" full width** - now spans 24 columns instead of 12
3. ✅ **Fixed device filter query** - changed to use `group()` before `distinct()` for better Grafana parsing

## Still Need Manual Fixes in Grafana

### Fix 1: Device Filter Labels (Bar Gauge)

The bar gauge needs to show device names instead of complex field names:

1. **Edit "Top Power Consumers" panel**
2. Go to **"Transform" tab**
3. Add transform: **"Labels to fields"**
   - Source label: `alias`
   - Destination field name: `device_name`
4. OR add transform: **"Organize fields"**
   - Show: `alias` and `_value`
   - Hide: everything else
   - Rename `alias` → "Device"

**OR simpler - Add field override:**
1. Panel → Edit → **"Field" tab**
2. Add override: **"Fields with name: _value"**
3. Set **"Display name"** to: `${__field.labels.alias}`

### Fix 2: Device Filter Dropdown

If the filter still shows nothing:

1. **Settings** → **Variables** → Edit `device_filter`
2. Try this query:
```flux
from(bucket: "rem")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "gos_rem")
  |> group(columns: ["alias"])
  |> distinct(column: "alias")
  |> sort()
  |> map(fn: (r) => ({_value: r.alias}))
```

3. Make sure:
   - Multi-value: ✅ ON
   - Include All: ✅ ON
   - Format: `AsIs`

4. Click "Apply" → Test - should see device names

---

## Re-import Option

If you want to start fresh with all fixes:
- File: `grafana/dashboards/GOS_REM_Dashboard_Working.json`
- Has: Table panel removed, bar gauge full width, improved device filter query

Then just need to fix the bar gauge labels manually (field override method above).

