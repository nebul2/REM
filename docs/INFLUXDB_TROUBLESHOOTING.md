# InfluxDB Troubleshooting - Exit Code 159

## Issue
InfluxDB container keeps restarting with exit code 159, indicating initialization failure.

## Current Status
- ✅ Collector: Working and collecting TP-Link data
- ✅ Grafana: Running and healthy  
- ✅ Admin UI: Running
- ❌ InfluxDB: Failing to initialize

## Troubleshooting Steps

### 1. Manual Initialization (Recommended)
Instead of automatic setup, try manual initialization:

```bash
# Start InfluxDB without automatic setup
docker run -d --name influxdb-manual \
  -p 7002:8086 \
  -v stats_influxdb-data:/var/lib/influxdb2 \
  influxdb:2.7-alpine

# Wait for it to start, then initialize via web UI:
# Open http://pi400:7002 in browser
# Or use CLI:
docker exec -it influxdb-manual influx setup \
  --username admin \
  --password <your-password> \
  --org GOS \
  --bucket rem \
  --token <your-token> \
  --force
```

### 2. Try Older InfluxDB Version
The 2.7-alpine image might have ARM compatibility issues:

```yaml
image: influxdb:2.6-alpine
```

### 3. Check System Resources
```bash
# Check available memory
free -h

# Check disk space
df -h

# Check Docker logs with more detail
docker compose logs influxdb --details 2>&1
```

### 4. Alternative: Use InfluxDB 1.x
If v2 continues to fail, consider using InfluxDB 1.x which has better ARM support:

```yaml
influxdb:
  image: influxdb:1.11-alpine
  # Different configuration needed for v1
```

## Temporary Workaround
The collector is working and can buffer data. You could:
1. Let collector run and log to files temporarily
2. Fix InfluxDB initialization
3. Import buffered data later

## Notes
- Exit code 159 = initialization script failure
- Platform mismatch warnings (arm64 vs arm/v8) may be contributing
- Empty logs suggest failure happens before logging initializes

