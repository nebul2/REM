# Import Clean Dashboard (No Filter Errors)

## The Problem
The device filter variable is causing JavaScript errors in Grafana. The errors are:
- "oe.replace is not a function"
- "le.create is not a function"

This is a Grafana variable parsing issue.

## Solution: Dashboard Without Device Filter

I've created a **clean dashboard** without the device filter variable that will load without errors.

### Import Steps

1. **Delete Current Dashboard**
   - Dashboards → Find your dashboard → ⋮ → Delete

2. **Import Clean Version**
   - Click "+" → "Import"
   - Upload: `grafana/dashboards/GOS_REM_Dashboard_Clean.json`
   - Select datasource: "InfluxDB"
   - Click "Import"

### What's Included

- ✅ **Total Power** panel
- ✅ **Power Consumption Over Time** graph (shows all devices)
- ✅ **Top Power Consumers** bar chart (shows all devices)
- ✅ **No device filter** (shows all devices - no filtering errors)
- ✅ **Clean device names** in bar gauge labels

### After Import

The dashboard will work immediately and show **all devices**. No filter errors!

### Add Device Filter Later (Optional)

Once the dashboard is working, you can add device filtering later:
1. Settings → Variables → New
2. Create a simple text variable or query variable
3. Test carefully to avoid the JavaScript errors

---

**File:** `grafana/dashboards/GOS_REM_Dashboard_Clean.json`
