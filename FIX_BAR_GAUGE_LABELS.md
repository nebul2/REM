# Fix Bar Gauge Labels - Show Device Aliases

## Problem
Top Power Consumers bar gauge shows complex field names instead of clean device names.

## Fix in Grafana

### Method 1: Add Transform (Easiest)

1. **Edit "Top Power Consumers" panel**
2. Go to **"Transform" tab**
3. Click **"Add transformation"**
4. Select: **"Organize fields"**
5. Configure:
   - **Hide:** All fields except keep `_value` and `alias`
   - **Rename:**
     - `alias` → "Device"
     - `_value` → "Power (W)"
6. **OR** use **"Labels to fields"** transform:
   - Source label: `alias`
   - Destination field: `device_name`

### Method 2: Add Field Override (Alternative)

1. Edit panel → **"Field" tab**
2. Scroll to **"Overrides"**
3. Click **"+ Add field override"**
4. Select: **"Fields with name"** → `_value`
5. Add property: **"Display name"** → `${__field.labels.alias}`

### Method 3: Fix Query (Best Solution)

The query should return alias as a separate field. Update the query to:

```flux
from(bucket: "rem")
  |> range(start: -10m)
  |> filter(fn: (r) => r._measurement == "gos_rem")
  |> filter(fn: (r) => r._field == "powerWatts")
  |> group(columns: ["alias"])
  |> mean()
  |> map(fn: (r) => ({ 
    r with 
    device: r.alias,
    power: r._value 
  }))
  |> sort(columns: ["power"], desc: true)
  |> limit(n: 15)
```

Then in field config, use `device` as the label field.

---

**Recommended:** Use Method 1 (Transform) - it's the easiest and most reliable.

