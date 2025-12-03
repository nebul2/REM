# Importing GOS REM Dashboard to Grafana

## Method 1: Import via Grafana UI (Recommended)

1. **Open Grafana**: http://localhost:7003

2. **Login**: 
   - Username: `admin`
   - Password: `stats-dev-password-2024` (or whatever you set in .env)

3. **Import Dashboard**:
   - Click the "+" icon in the left sidebar
   - Select "Import"
   - Click "Upload JSON file"
   - Navigate to: `/Users/d2/Desktop/cursor-devbench/gos/stats/grafana/dashboards/GOS_REM_Dashboard.json`
   - Click "Load"
   - Select "InfluxDB" as the datasource
   - Click "Import"

4. **Dashboard Features**:
   - ✅ **Device Filter**: Multi-select dropdown to filter specific devices
   - ✅ **Interval Selector**: Choose aggregation interval (10s, 30s, 1m, 5m, etc.)
   - ✅ **Total Power**: Sum of all selected devices
   - ✅ **Time Series Graph**: Power consumption over time
   - ✅ **Top Consumers**: Bar chart of highest power devices
   - ✅ **Current Power Table**: Table showing current power for each device

## Method 2: Copy-Paste JSON

1. Open Grafana → "+" → "Import"
2. Copy the contents of `GOS_REM_Dashboard.json`
3. Paste into the JSON text area
4. Click "Load" and follow steps above

## Dashboard Features Explained

### Device Filter
- Located at the top of the dashboard
- Multi-select dropdown showing all available devices
- Default: "All" (shows all devices)
- Select specific devices to filter data

### Time Range
- Use the time picker in the top right
- Default: Last 1 hour
- Can change to custom ranges, last 24 hours, etc.

### Panels

1. **Total Power (Watts)**
   - Shows sum of all selected devices
   - Updates in real-time

2. **Power Consumption by Device**
   - Time series graph
   - Shows power over time for selected devices
   - Use legend to show/hide specific devices

3. **Top Power Consumers**
   - Bar chart of highest power devices (last 10 minutes)
   - Shows top 15 devices

4. **Current Power by Device**
   - Table showing current power reading for each device
   - Sorted by power (highest first)

## Customizing the Dashboard

### Add Energy Totals Panel

To add energy (kWh) calculation, add this query in a new panel:

```flux
from(bucket: "rem")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "gos_rem")
  |> filter(fn: (r) => r._field == "powerWatts")
  |> filter(fn: (r) => contains(value: r.alias, set: ${device_filter:json}))
  |> group(columns: ["alias"])
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
  |> integral(unit: 1h)
  |> map(fn: (r) => ({ r with _value: r._value / 1000.0 }))
  |> group()
  |> sum()
```

Set unit to "kWh" to show energy consumption.

### Add Time Comparison

To compare two time periods:

1. Create a new panel
2. Use two queries with different time ranges
3. Use variables for time offset (e.g., `now-2h` vs `now-1h`)

## Troubleshooting

### "No Data" in Panels

1. Check device filter - make sure devices are selected
2. Check time range - make sure it includes recent data
3. Check datasource - verify "InfluxDB" datasource is selected
4. Check query - verify bucket name is "rem"

### Devices Not Showing in Filter

- Wait a few minutes for data to populate
- Check that collector is running: `docker-compose logs collector`
- Verify data exists: Use Explore tab to query manually

### Query Errors

- Ensure datasource token is correct
- Check bucket name: should be "rem"
- Verify organization: should be "GOS"
- Check measurement name: should be "gos_rem"

## Next Steps

- Customize panels for your needs
- Add alerts for high power consumption
- Create multiple dashboards for different views
- Export dashboard JSON for backup

