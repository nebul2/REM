# Current System Assessment - Pi400 Setup

## Overview
Assessed the existing TP-Link to InfluxDB energy monitoring system running on your Raspberry Pi 400. Here's what I found:

---

## System Architecture (Current)

### Hardware & OS
- **Device**: Raspberry Pi 400 (ARM64)
- **OS**: Debian-based Raspberry Pi OS (Kernel 6.1.0-rpi8-rpi-v8)
- **Location**: Accessible via SSH at `pi400`

### Services Running
1. **InfluxDB 2.x**
   - System service (influxdb.service)
   - Running on port 8086 (HTTP)
   - Organization: "GOS"
   - Bucket: "rem" (Remote Energy Measurement)
   - Started: October 24, 2024

2. **Grafana 10.4.2**
   - System service
   - Running on port 3000
   - Health check: ✅ Working (commit: 22809dea5)
   - Started: October 24, 2024

3. **Data Collector (Python)**
   - Script: `/home/d2/tplink_to_influxdb/app/cloudcollect.py`
   - Virtual environment: `.venv` in project directory
   - Execution: Via cron job every minute

---

## Code Structure

### Main Project Directory
```
/home/d2/tplink_to_influxdb/
├── app/
│   ├── cloudcollect.py         # Main collector (ACTIVE)
│   ├── cloudcollect.py.old     # Backup
│   ├── cloudcollect.py.restore # Backup
│   ├── collect.py              # Alternative version (not used)
│   ├── refreshTokenfile.txt    # OAuth refresh token (IMPORTANT)
│   └── .venv/                  # Python virtual environment
├── config.yaml                 # Active configuration
├── example/
│   └── config.yml              # Example configuration
├── README.md                   # Documentation
├── Dockerfile                  # Docker support (not currently used)
├── query.sh                    # Legacy script
├── cloudquery.sh               # Legacy script
└── .git/                       # Git repository
```

### Python Dependencies (from .venv)
```python
influxdb-client==1.40.0    # InfluxDB v2 client
PyP100==0.1.4              # TP-Link Tapo P110 control
python-kasa==0.6.2.1       # TP-Link Kasa control (alternative)
PyYAML                     # Config file parsing
requests                   # HTTP client
```

---

## Current Workflow

### 1. Cron Job Schedule
```cron
* * * * * /home/d2/tplink_to_influxdb/app/cloudcollect.py
```
- **Frequency**: Every minute
- **Issue**: Script runs in loop mode (persist: true) so shouldn't be in cron
- **Result**: Multiple zombie processes (~80+ orphaned processes found)

### 2. Data Collection Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. Cron triggers cloudcollect.py every minute          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Get OAuth Access Token                               │
│    • Read refresh token from file                       │
│    • POST to TP-Link auth endpoint                      │
│    • Get new access + refresh tokens                    │
│    • Save new refresh token to file                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Get Device List                                       │
│    • POST to /v1/getDeviceList                          │
│    • Filter for online P110/P110M models                │
│    • Extract device IDs and aliases                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Poll Each Device (Loop)                              │
│    • POST to /v1/device/deviceControl                   │
│    • Method: "getDeviceRealTimeEnergy"                  │
│    • Response: powerWatts value                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Write to InfluxDB                                     │
│    • Measurement: "gos_rem"                             │
│    • Tag: alias (device name)                           │
│    • Field: powerWatts (float)                          │
│    • Timestamp: nanosecond precision                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 6. Sleep & Repeat (if persist: true)                    │
│    • Sleep for interval (10 seconds)                    │
│    • Loop back to step 2                                │
└─────────────────────────────────────────────────────────┘
```

---

## Configuration Analysis

### Active Configuration (config.yaml)
```yaml
poller:
    persist: true        # ⚠️ Runs in infinite loop
    interval: 10         # Poll every 10 seconds

influxdb:
    -
        name: "TPLINKDB"
        url: "http://127.0.0.1:8086"
        token: "gwTu1qAtPgIRU8eWNpLXuz92pKo6_lgV7Y4mhdMM7n_XOe-fTXts7T54P_FQJ69UMVuTyhr77Ly7XCGz9QUNAA=="
        org: "GOS"
        bucket: "rem"

# Note: No device list in config - fetched from cloud
```

### TP-Link Cloud API Details
```python
# OAuth Endpoints
AUTH_URL = "https://aps1-openapi.tplinknbu.com/v1/oauth/token"
DEVICE_LIST_URL = "https://aps1-openapi.tplinknbu.com/v1/getDeviceList"
DEVICE_CONTROL_URL = "https://aps1-openapi.tplinknbu.com/v1/device/deviceControl"

# OAuth Credentials (in code)
CLIENT_ID = "fdcae128-0adf-4233-8a58-30760652bd16"
CLIENT_SECRET = "4087d4b9-5e0c-4e50-b06c-22580fc618d5"
API_KEY = "e71bf02f-8b71-42ee-8af0-62a7bdf6c866"

# User must manually get initial authorization code from:
# https://aps1-openapi.tplinknbu.com/v1/oauth/authorize?
#   client_id=fdcae128-0adf-4233-8a58-30760652bd16
#   &response_type=code
#   &scope=all
#   &state=123456789012345678901234
#   &redirect_uri=https://www.greeningofstreaming.org
```

---

## Critical Issues Found

### 🔴 Issue 1: Zombie Processes
**Problem**: ~80+ orphaned Python processes running
```
d2        3603  0.0  0.8  38440 31648 ?        S    Nov11   0:07 cloudcollect.py
d2        8043  0.0  0.8  38424 31644 ?        S    Oct29   0:10 cloudcollect.py
d2       14318  0.0  0.8  38440 31648 ?        S    Nov03   0:03 cloudcollect.py
... (75+ more)
```

**Cause**: 
- Script has `persist: true` (runs in infinite loop)
- Cron launches new instance every minute
- Old instances never terminate
- Each holds 30+ MB RAM

**Impact**: 
- Memory waste (~2.4 GB)
- System performance degradation
- Possible data duplication

**Fix**: 
- Either: Remove from cron, run as systemd service
- Or: Set `persist: false` in config

### 🟡 Issue 2: Hard-coded Paths
**Problem**: Paths are absolute to Pi400
```python
CONF_FILE = os.getenv("CONF_FILE", "/home/d2/tplink_to_influxdb/example/config.yml")
refreshTokenfile = open("/home/d2/tplink_to_influxdb/app/refreshTokenfile.txt","r+")
```

**Impact**: Not portable to containers or other systems

**Fix**: Use relative paths or environment variables

### 🟡 Issue 3: Credentials in Code
**Problem**: 
- OAuth credentials hard-coded in Python file
- TP-Link user/pass in config.yaml (commented out in example)
- InfluxDB token in config.yaml

**Impact**: Security risk, can't share code publicly

**Fix**: Move to environment variables or secrets management

### 🟡 Issue 4: No Error Recovery
**Problem**: Basic error handling
```python
# No retry logic for API failures
# No alerting on token refresh failure
# No health check endpoint
```

**Impact**: Silent failures, data gaps

**Fix**: Add robust error handling, retry logic, monitoring

### 🟡 Issue 5: Limited Dashboards
**Problem**: From README: "grafana representations are quite simple"

**Needs**:
- Device filtering (select specific devices)
- Time range filtering (experiments between specific times)
- More advanced visualizations
- Energy totals (kWh)
- Cost estimation

---

## Data Model

### InfluxDB Structure
```
Organization: GOS
Bucket: rem (Remote Energy Measurement)
Measurement: gos_rem

Point Schema:
{
  "measurement": "gos_rem",
  "tags": {
    "alias": "Device-Location-Name"  // e.g., "London Office - PC"
  },
  "fields": {
    "powerWatts": 42.5  // Current power consumption
  },
  "time": 1733140800000000000  // Nanosecond timestamp
}
```

### Example Data Point
```
gos_rem,alias=Stockholm-Encoder-01 powerWatts=125.3 1733140800000000000
gos_rem,alias=London-Office-PC powerWatts=87.2 1733140800000000000
```

---

## Positive Aspects

### ✅ What's Working Well
1. **Stable Core Functionality**
   - InfluxDB running continuously since Oct 24
   - Grafana accessible and healthy
   - Data collection working (despite process issues)

2. **Good API Design**
   - TP-Link Cloud API provides centralized access
   - No need to poll devices on local network
   - Devices can be anywhere on internet

3. **Existing Documentation**
   - README.md with usage instructions
   - Based on established bentasker/tplink_to_influxdb project
   - Example configs provided

4. **Docker-Ready**
   - Dockerfile already exists (not used yet)
   - Code can be containerized
   - Good foundation for migration

5. **Flexible Configuration**
   - YAML-based config
   - Support for multiple InfluxDB outputs
   - Configurable polling intervals

---

## Code Quality Assessment

### cloudcollect.py Analysis

**Strengths**:
- Clear function separation (getToken, getDeviceList, getDevPower)
- Support for multiple InfluxDB destinations
- Token refresh automation
- Configurable persist mode

**Weaknesses**:
- Hard-coded credentials
- Hard-coded file paths
- No logging (only print statements)
- No structured error handling
- No retry logic
- No health check endpoint
- No graceful shutdown handling

**Improvements Needed**:
```python
# Current
print(stats)

# Should be
logger.info("Collected data from device", extra={"device_id": deviceId, "watts": devPower})

# Current
refreshTokenfile = open("/home/d2/tplink_to_influxdb/app/refreshTokenfile.txt","w")

# Should be
token_file = os.getenv("TOKEN_FILE_PATH", "/config/refresh_token.txt")

# Current (missing)
# Add health check endpoint
# Add signal handlers for graceful shutdown
# Add retry with exponential backoff
```

---

## Performance Characteristics

### Current Load
- **Poll interval**: 10 seconds
- **Devices**: Unknown count (fetched from cloud)
- **API calls per hour**: 6 per device (360/hour assuming 1 device)
- **Database writes**: 6 per device per minute
- **Memory usage**: ~30 MB per process (should be 1 process, currently 80+)

### Optimization Opportunities
1. **Reduce zombie processes** → Save ~2.4 GB RAM
2. **Batch writes to InfluxDB** → Already doing this ✅
3. **Connection pooling** → Not implemented
4. **Caching device list** → Fetch once, cache for X minutes

---

## Migration Readiness

### Ready to Migrate
- ✅ Core logic is sound
- ✅ InfluxDB data can be backed up
- ✅ Configuration is file-based
- ✅ Docker support exists

### Needs Work Before Migration
- ⚠️ Fix hard-coded paths
- ⚠️ Move credentials to env vars
- ⚠️ Add proper logging
- ⚠️ Add health checks
- ⚠️ Improve error handling
- ⚠️ Fix process management issue

### Data Migration
```bash
# Backup InfluxDB data
ssh pi400 "influx backup /tmp/influx-backup -t <token>"

# Copy to local
scp -r pi400:/tmp/influx-backup ./backup/

# Restore to container
docker exec stats-influxdb influx restore /backup/
```

---

## Recommendations

### Immediate (This Week)
1. **Fix zombie processes** on Pi400
   ```bash
   # Stop cron job
   crontab -e  # Comment out the line
   
   # Kill old processes
   pkill -f cloudcollect.py
   
   # Run as systemd service instead
   sudo systemctl enable tplink-collector
   ```

2. **Create container version** with fixes
   - Remove hard-coded paths
   - Add environment variable support
   - Add proper logging
   - Add health check endpoint

3. **Test locally** with Docker Compose
   - Verify data collection works
   - Test token refresh
   - Monitor for errors

### Short-term (Next 2 Weeks)
4. **Enhance Grafana dashboards**
   - Add device filtering
   - Add time range comparison
   - Add energy totals

5. **Deploy to cloud**
   - Choose Linode instance
   - Set up deployment scripts
   - Migrate data

### Long-term (Month 1-2)
6. **Build admin interface**
   - Start/stop collection
   - Configure polling
   - View status

7. **Add monitoring & alerting**
   - Uptime monitoring
   - Data gap alerts
   - API error alerts

---

## Questions & Next Steps

### Information Needed
1. **TP-Link API**: Do you have rate limit documentation?
2. **Device count**: How many P110 devices are in the GOS network?
3. **Deployment timeline**: When do you need this running on Linode?
4. **Access**: Who needs access to Grafana/Admin interface?

### Proposed Next Actions
1. ✅ Create project plan (completed)
2. ✅ Document current state (this document)
3. → Improve Python collector script
4. → Create docker-compose.yml
5. → Test local deployment
6. → Deploy to cloud

---

**Assessment Date**: 2025-12-02  
**Pi400 Status**: Operational (but needs cleanup)  
**Readiness**: 70% - Good foundation, needs refinement  
**Risk Level**: Low - Can run in parallel with Pi400 during testing


