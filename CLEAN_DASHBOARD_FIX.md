# Quick Manual Fixes for Dashboard Metadata

## Issue 1: Device Names Showing as "powerWatts Arian STB"

**Fix in Grafana:**

1. **Edit "Power Consumption Over Time" panel**
2. Click **"Field" tab** (right sidebar)
3. Scroll to **"Overrides"** section
4. Click **"+ Add field override"**
5. Select: **"Fields with name"** → Enter: `powerWatts`
6. Add override:
   - Property: **"Display name"**
   - Value: `${__field.labels.alias}` (this uses the device alias from the tag)
7. Click **"Apply"**

**Alternative - Use Transform:**
1. Edit panel → **"Transform" tab**
2. Add transform: **"Organize fields"**
3. Hide: `_field`, `_measurement`
4. Show: `_value`, `alias`
5. Or add: **"Labels to fields"** transform to extract alias

---

## Issue 2: Active Devices Panel Showing Messy Data

**Fix:**

1. **Edit "Active Devices" panel**
2. Go to **"Field" tab**
3. Add override:
   - Field: `_value` (or whatever field shows the count)
   - Hide: All other fields
4. Or **simplify the query** - it should just return a number

**Check the query is correct:**
```flux
from(bucket: "rem")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "gos_rem")
  |> filter(fn: (r) => r._field == "powerWatts")
  |> group(columns: ["alias"])
  |> last()
  |> count()
```

This should return just one number. If it's showing multiple rows, the panel display is wrong.

**Quick fix:**
- In panel options, set "Reduce" to show only the count
- Hide all fields except the count value

---

## Issue 3: Table Showing Confusing Columns

**Fix:**

1. **Edit "Current Power by Device" panel**
2. **"Field" tab** → **"Overrides"**
3. Add overrides to:
   - **Hide:** `_time`, `_field`, `_measurement`, `_start`, `_stop`, `_result`
   - **Show only:** `alias` and `_value`
   - **Rename:**
     - `alias` → "Device"
     - `_value` → "Power (W)"

**OR use Transform:**
1. **"Transform" tab**
2. Add: **"Organize fields"**
3. Hide technical fields
4. Keep only: `alias` (rename to "Device") and `_value` (rename to "Power (W)")

---

## Quick Fix Summary

For each panel:
1. Click panel → Edit
2. "Field" tab → Overrides
3. Hide technical fields (`_field`, `_measurement`, `_time`, etc.)
4. Show only meaningful data
5. Rename fields to readable names

**For graphs:** Use `${__field.labels.alias}` as display name to show just device name.

---

I'll create a fixed dashboard JSON with all these overrides pre-configured!

