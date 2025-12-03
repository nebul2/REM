# Quick Start Guide - GOS Stats

## Next Steps: Test Locally

### Step 1: Get Credentials from Pi400

```bash
# SSH to pi400 and extract refresh token
ssh pi400 "cat /home/d2/tplink_to_influxdb/app/refreshTokenfile.txt"
```

Copy the refresh token value - you'll need it for the `.env` file.

### Step 2: Create Environment File

```bash
cd /Users/d2/Desktop/cursor-devbench/gos/stats
cp ENV_TEMPLATE .env
```

Then edit `.env` and set:
```bash
TPLINK_REFRESH_TOKEN=your-token-from-pi400-here
INFLUXDB_ADMIN_PASSWORD=some-secure-password
GRAFANA_ADMIN_PASSWORD=some-secure-password
```

### Step 3: Start Docker Stack

```bash
docker-compose up -d
```

This will:
- Build the collector container
- Start InfluxDB on port 7002
- Start Grafana on port 7003
- Start the collector service

### Step 4: Check Logs

```bash
# Watch collector logs
docker-compose logs -f collector

# Should see:
# - "Starting GOS Remote Energy Measurement Collector"
# - "Found X online P110 devices"
# - "Collected XX.XW from DeviceName"
```

### Step 5: Access Services

- **Grafana**: http://localhost:7003
  - Login: `admin` / (password from .env)
  - Check InfluxDB datasource connection

- **InfluxDB**: http://localhost:7002
  - Username: `admin`
  - Password: (from .env)

### Step 6: Verify Data Collection

Wait ~30 seconds for first poll, then:

```bash
# Check if data is in InfluxDB
docker exec stats-influxdb influx query \
  'from(bucket:"rem") |> range(start:-1h) |> count()' \
  --token YOUR_TOKEN
```

---

## Troubleshooting

### Collector Can't Get Token
- Check `TPLINK_REFRESH_TOKEN` in .env
- Token might be expired - may need to get new one

### No Devices Found
- Check collector logs for API errors
- Verify TP-Link API credentials are correct
- Check if devices are online in TP-Link app

### No Data in Grafana
- Verify InfluxDB datasource is connected in Grafana
- Check collector is writing: `docker-compose logs collector | grep "Wrote"`
- Wait for collector to complete first poll cycle (30s)

### Port Already in Use
```bash
# Check what's using ports
lsof -i :7002
lsof -i :7003

# Change ports in docker-compose.yml if needed
```

---

## What's Next After Local Testing?

Once local testing works:

1. **Deploy to Pi400** (see DEPLOYMENT.md)
   - Copy files to pi400
   - Set up .env with credentials
   - Run in parallel with native services
   - Verify data matches

2. **Migrate Production**
   - Stop native services
   - Switch ports to production (8086, 3000)
   - Clean up old installation

3. **Enhance Dashboards**
   - Add device filtering
   - Add time range comparisons
   - Add energy totals

---

**Ready to test!** Start with Step 1 above. 🚀

