# Fix Dashboard Metadata Issues

## Problems
1. Device names showing as "powerWatts Arian STB" instead of just "Arian STB"
2. "Active Devices" panel showing raw data overlay instead of clean count
3. Table showing confusing column names

## Quick Manual Fixes

### Fix 1: Clean Device Names in Graph Legend

1. Click "Power Consumption Over Time" panel → Edit
2. Go to "Field" tab (on right sidebar)
3. Find "Overrides" section
4. Click "Add field override"
5. Select: "Fields with name: powerWatts"
6. Add these overrides:
   - **Display name:** Set to `${__field.labels.alias}` (this uses the alias tag)
   - OR manually add override: "Name: powerWatts" → "Display name: `${__field.labels.alias}`"

**Better approach - Use Transform:**
1. Click panel → Edit → "Transform" tab
2. Add transform: "Organize fields"
3. Hide: `_field`, `_measurement`, `_start`, `_stop`
4. Show: `_value` and `alias`

### Fix 2: Fix Active Devices Panel

1. Click "Active Devices" panel → Edit
2. Check the query - it should just return a count
3. If showing raw data, add transformation:
   - Transform tab → Add "Reduce" transform
   - Mode: "Single field"
   - Calculation: "Last value"
   - OR just use the stat panel's reduce options properly

### Fix 3: Clean Table Display

1. Click "Current Power by Device" panel → Edit
2. Field tab → Add overrides:
   - Hide `_time`, `_field`, `_measurement`, `_start`, `_stop`
   - Show only `alias` and `_value`
   - Rename `_value` to "Power (W)"
   - Rename `alias` to "Device"

OR use Transform:
1. Transform tab → Add "Organize fields"
2. Hide all technical fields
3. Show only `alias` and `_value`
4. Rename them appropriately

## Automated Fix - Dashboard JSON Update

I'll create a fixed dashboard JSON with proper field overrides configured.

