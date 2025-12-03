# Quick Dashboard Import

## Import Steps (30 seconds)

1. **Open Grafana**: http://localhost:7003
   - Login: `admin` / `stats-dev-password-2024`

2. **Import Dashboard**:
   - Click **"+"** (plus icon) → **"Import"**
   - Click **"Upload JSON file"**
   - Select: `grafana/dashboards/GOS_REM_Dashboard.json`
   - Click **"Load"**
   - Select datasource: **"InfluxDB"**
   - Click **"Import"**

3. **Done!** You should now see:
   - Total Power display
   - Power consumption graph
   - Top consumers bar chart
   - Current power table
   - Device filter dropdown (top of dashboard)

## Features

✅ **Device Filter** - Select specific devices to view
✅ **Time Range** - Change time window (top right)
✅ **Auto-refresh** - Updates every 30 seconds
✅ **Multiple Views** - Graph, bars, table, stats

## Dashboard Location

After import, dashboard will be at:
**Dashboards → GOS Remote Energy Measurement (REM)**

---

**Need help?** See `DASHBOARD_IMPORT.md` for detailed instructions.

