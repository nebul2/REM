# GOS Remote Energy Measurement (REM) System - Project Plan

## Executive Summary

This project migrates the Greening of Streaming (GOS) energy measurement system from a Raspberry Pi 400 installation to a fully containerized, cloud-deployable solution. The system collects real-time power consumption data from TP-Link Tapo P110 smart plugs distributed globally, stores it in InfluxDB, and visualizes it through Grafana dashboards.

**Primary Goal**: Create a portable, scalable, and easily deployable Docker-based solution that can run on Akamai Linode or similar cloud platforms.

---

## Current State Analysis

### Infrastructure (Pi400)
- **Hardware**: Raspberry Pi 400 (ARM64)
- **OS**: Debian-based Raspberry Pi OS
- **Services**: 
  - InfluxDB 2.x (running as system service on port 8086)
  - Grafana 10.4.2 (running as system service on port 3000)
  - Python collector script (via cron every minute)

### Existing Code
- **Location**: `/home/d2/tplink_to_influxdb/`
- **Main Script**: `app/cloudcollect.py`
- **Config**: `config.yaml` and `example/config.yml`
- **Based on**: [bentasker12/tplink_to_influxdb](https://github.com/bentasker/tplink_to_influxdb)

### Current Workflow
1. **Cron Job**: Runs every minute (`* * * * *`)
2. **Authentication**: 
   - Uses TP-Link Cloud API (OAuth2 with refresh tokens)
   - Client ID: `fdcae128-0adf-4233-8a58-30760652bd16`
   - API endpoint: `https://aps1-openapi.tplinknbu.com/v1/`
3. **Data Collection**:
   - Fetches device list (filters for P110/P110M models)
   - Polls each device for real-time power (watts)
   - Writes to InfluxDB measurement `gos_rem`
4. **Polling Interval**: Currently 10 seconds (configurable in `config.yaml`)

### Critical Issues Found
1. **Multiple Zombie Processes**: ~80+ hung Python processes from failed cron jobs
2. **Hard-coded Paths**: Script uses `/home/d2/` paths - not portable
3. **No Process Management**: Cron-based execution causes orphaned processes
4. **Limited Admin Interface**: No way to pause/resume data collection
5. **No Advanced Filtering**: Grafana dashboards are basic
6. **Credentials in Code**: API credentials and tokens in config files

### Data Model
- **Measurement**: `gos_rem`
- **Tags**: 
  - `alias`: Device name/location
- **Fields**:
  - `powerWatts`: Current power consumption (float)
- **Timestamp**: Nanosecond precision

---

## Architecture Design

### Container Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │  Data Collector │  │   InfluxDB 2.x  │  │  Grafana    │ │
│  │   (Python App)  │──│   (Database)    │──│ (Dashboard) │ │
│  │                 │  │                 │  │             │ │
│  │ • TP-Link API   │  │ • Time-series   │  │ • Visualize │ │
│  │ • OAuth refresh │  │ • Retention     │  │ • Filter    │ │
│  │ • Config mgmt   │  │ • Backup        │  │ • Export    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│          │                     │                    │        │
│          └─────────────────────┴────────────────────┘        │
│                              │                                │
│                    ┌─────────────────────┐                   │
│                    │   Admin Web UI      │                   │
│                    │   (Optional Flask)  │                   │
│                    │ • Start/Stop collect│                   │
│                    │ • Config management │                   │
│                    │ • Status monitoring │                   │
│                    └─────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────────────────┐
                    │  TP-Link Cloud API  │
                    │  (External)         │
                    └─────────────────────┘
```

### Component Details

#### 1. Data Collector (Python)
- **Base Image**: `python:3.11-slim`
- **Dependencies**:
  - `influxdb-client==1.40.0`
  - `PyP100==0.1.4` (or updated fork)
  - `python-kasa==0.6.2.1`
  - `PyYAML`
  - `requests`
- **Features**:
  - Configurable polling interval (1-300 seconds)
  - OAuth2 token refresh automation
  - Graceful error handling
  - Health check endpoint
  - Pause/resume via signal handling
  - Environment-based configuration

#### 2. InfluxDB 2.x
- **Base Image**: `influxdb:2.7-alpine`
- **Configuration**:
  - Organization: `GOS`
  - Bucket: `rem` (Remote Energy Measurement)
  - Retention: Configurable (default 90 days)
  - Admin token: Environment variable
- **Volumes**:
  - `/var/lib/influxdb2`: Data persistence
  - `/etc/influxdb2`: Configuration

#### 3. Grafana
- **Base Image**: `grafana/grafana:10.4.2`
- **Features**:
  - Pre-configured InfluxDB datasource
  - Advanced dashboard with:
    - Device filtering (multi-select)
    - Time range picker
    - Power consumption graphs
    - Energy totals (Wh/kWh)
    - Real-time updates
    - Comparison views
    - Export capabilities
- **Volumes**:
  - `/var/lib/grafana`: Dashboard persistence
  - `/etc/grafana/provisioning`: Auto-provisioning

#### 4. Admin Web UI (Optional Phase 2)
- **Framework**: Flask or FastAPI
- **Features**:
  - Start/stop data collection
  - Configure polling interval
  - View collector status
  - Manage device list
  - View logs
  - Health check dashboard

---

## Deployment Targets

### Local Development
- Docker Compose on macOS/Linux
- Port mapping:
  - 7001: Admin UI
  - 7002: InfluxDB
  - 7003: Grafana

### Akamai Linode (Primary Target)
- **Service**: Linode Kubernetes Engine (LKE) or Compute Instance
- **Option A - Compute Instance**:
  - Smallest instance ($5/month)
  - Docker + Docker Compose
  - Simple deployment
  - Manual scaling
  
- **Option B - LKE (Kubernetes)**:
  - More complex setup
  - Better for scale
  - Higher cost (~$30/month minimum)
  - Auto-scaling, load balancing

### Alternative: Serverless Architecture
Similar to RAMS/Meetex on Google Cloud Run:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Cloud Run      │────▶│  Cloud SQL or   │────▶│  Grafana Cloud  │
│  (Collector)    │     │  InfluxDB Cloud │     │  (Visualization)│
│                 │     │                 │     │                 │
│ • Scheduled run │     │ • Managed DB    │     │ • Free tier     │
│ • Cloud Scheduler│    │ • Auto-backup   │     │ • Or self-host  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

**Pros**: Lower cost when idle, fully managed  
**Cons**: Cold starts, more complex state management

---

## Implementation Phases

### Phase 1: Core Containerization (Week 1) ✅ CURRENT
**Goal**: Get basic Docker stack running locally

- [x] Create project structure
- [x] Analyze existing Pi400 setup
- [ ] Create improved Python collector
  - Remove hard-coded paths
  - Add environment variable support
  - Improve error handling
  - Add health check endpoint
  - Implement graceful shutdown
- [ ] Create docker-compose.yml
- [ ] Set up InfluxDB container
- [ ] Set up Grafana container
- [ ] Test local deployment

**Deliverable**: Working Docker Compose stack on local machine

### Phase 2: Enhanced Features (Week 1-2)
**Goal**: Add configuration management and improved dashboards

- [ ] Configuration system
  - YAML config with env var overrides
  - Secrets management (not in Git)
  - Multiple profile support (dev/staging/prod)
- [ ] Enhanced Grafana dashboards
  - Device multi-select filter
  - Time range comparison
  - Energy consumption totals
  - Cost estimation (if rates provided)
  - Real-time alerting
- [ ] Data retention policies
- [ ] Backup/restore scripts

**Deliverable**: Production-ready configuration system

### Phase 3: Admin Interface (Week 2)
**Goal**: Web-based administration

- [ ] Flask/FastAPI admin app
- [ ] Status dashboard
- [ ] Start/stop/pause controls
- [ ] Configuration editor (safe)
- [ ] Log viewer
- [ ] Health checks

**Deliverable**: Admin web interface

### Phase 4: Cloud Deployment (Week 2-3)
**Goal**: Deploy to Akamai Linode

- [ ] Linode account setup
- [ ] Choose deployment method (Compute vs LKE)
- [ ] Create deployment scripts
- [ ] Set up DNS (if needed)
- [ ] Configure SSL/TLS
- [ ] Test cloud deployment
- [ ] Document deployment process

**Deliverable**: Running system on Linode

### Phase 5: Documentation & Handoff (Week 3)
**Goal**: Enable GOS community to operate system

- [ ] User documentation
  - Quick start guide
  - Configuration guide
  - Dashboard usage
  - Troubleshooting
- [ ] Admin documentation
  - Deployment guide
  - Backup/restore procedures
  - Cost monitoring
  - Scaling guide
- [ ] Video walkthrough (optional)

**Deliverable**: Complete documentation

---

## Technical Decisions

### 1. Polling Frequency
**Current**: 10 seconds  
**Recommendation**: Start with 30 seconds, make configurable

**Rationale**:
- TP-Link API rate limits unknown
- 30s = ~3,000 API calls/day per device
- Provides good data resolution
- Lower risk of API throttling
- Can be adjusted based on testing

### 2. Data Retention
**Recommendation**: 
- Raw data: 90 days
- Downsampled (1min avg): 1 year
- Downsampled (1hr avg): 5 years

### 3. Database Choice
**Decision**: Keep InfluxDB 2.x

**Rationale**:
- Already in use, working well
- Excellent for time-series data
- Self-hostable (cost control)
- Good Grafana integration
- Migration path to InfluxDB Cloud if needed

**Alternative Considered**: Postgres with TimescaleDB
- Pros: More familiar, flexible
- Cons: More complex setup, less time-series optimized

### 4. Deployment Method (Linode)
**Recommendation**: Start with Compute Instance + Docker Compose

**Rationale**:
- Simple to set up
- Low cost ($5-10/month)
- Easy to manage
- Sufficient for current scale
- Can migrate to K8s later if needed

### 5. Secrets Management
**Options**:
1. **Environment variables** (initial)
2. **HashiCorp Vault** (if scale increases)
3. **Linode Secrets Manager** (if available)

**Decision**: Start with env vars, plan for Vault

---

## Cost Estimation

### Akamai Linode
- **Compute Instance**: $5-10/month
  - 1GB RAM (sufficient for light load)
  - 25GB storage
- **Backup**: $2/month (optional)
- **DNS**: Free
- **Total**: ~$7-12/month

### Alternative: InfluxDB Cloud + Grafana Cloud
- **InfluxDB Cloud**: Free tier (limited) or $50+/month
- **Grafana Cloud**: Free tier (14 days) or $49+/month
- **Cloud Run**: ~$0-5/month (depends on usage)
- **Total**: $0-100+/month

**Recommendation**: Self-hosted on Linode for cost control

---

## Performance Requirements

### Data Volume Estimation
- **Devices**: Assume 20-50 P110 plugs
- **Poll interval**: 30 seconds = 2,880 readings/day per device
- **Data per reading**: ~100 bytes
- **Daily data**: 50 devices × 2,880 × 100 bytes = ~14 MB/day
- **90 days retention**: ~1.3 GB

**Conclusion**: Very light load, basic instance sufficient

### API Rate Limits
- **TP-Link Cloud API**: Limits unknown, needs testing
- **Safety margin**: Start conservative (30s), monitor for errors
- **Backoff strategy**: Exponential backoff on API errors

---

## Security Considerations

### Secrets
- [ ] TP-Link API credentials (client ID/secret)
- [ ] TP-Link refresh token
- [ ] InfluxDB admin token
- [ ] Grafana admin password

**Storage**:
- `.env` file (gitignored)
- DevBench secrets management
- Optionally: Vault integration

### Network
- [ ] Grafana behind authentication
- [ ] InfluxDB not exposed publicly
- [ ] Admin UI (if built) behind auth
- [ ] SSL/TLS for public interfaces

### API Access
- [ ] Read-only Grafana dashboards for wider team
- [ ] Admin access restricted
- [ ] API token rotation (future)

---

## Migration Plan

### From Pi400 to Container

1. **Backup Current Data**
   ```bash
   # On Pi400
   influx backup /tmp/influx-backup -t <token>
   ```

2. **Stop Pi400 Services**
   ```bash
   sudo systemctl stop influxdb grafana-server
   crontab -e  # Comment out cron job
   ```

3. **Deploy Container Stack**
   ```bash
   # On new system
   docker-compose up -d
   ```

4. **Restore Data**
   ```bash
   docker exec -it stats-influxdb influx restore /backup/
   ```

5. **Verify & Test**
   - Check data in Grafana
   - Confirm new data collecting
   - Monitor for 24 hours

6. **Decommission Pi400**
   - Keep as backup for 30 days
   - Archive final data backup

---

## Risk Mitigation

### Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| API rate limiting | Data loss | Conservative polling, backoff strategy, monitoring |
| Token expiry | Collection stops | Robust refresh logic, alerting |
| Database full | Data loss | Retention policies, monitoring, alerts |
| Container crashes | Downtime | Health checks, auto-restart, monitoring |
| Cost overruns | Budget issues | Choose right-sized instance, set billing alerts |
| Data loss | Experiment failure | Regular backups, retention policies |

---

## Success Criteria

### Phase 1 (Local) ✅
- [ ] Docker stack runs on local machine
- [ ] Data collection works
- [ ] Grafana shows data
- [ ] Configuration via files (not hard-coded)

### Phase 2 (Features) ✅
- [ ] Advanced Grafana dashboards with filtering
- [ ] Configurable polling interval
- [ ] Multiple environment support
- [ ] Documentation complete

### Phase 3 (Cloud) ✅
- [ ] Running on Linode
- [ ] Accessible to GOS team
- [ ] Data collecting 24/7
- [ ] Cost within budget ($10/month)

### Phase 4 (Operations) ✅
- [ ] GOS team can pause/resume collection
- [ ] GOS team can view/export data
- [ ] GOS team can add/remove devices
- [ ] System self-healing (restarts on failure)

---

## Next Steps

### Immediate (This Session)
1. ✅ Assess current Pi400 setup
2. ✅ Create project plan
3. → Create project structure
4. → Improve Python collector script
5. → Create docker-compose.yml
6. → Test local deployment

### This Week
- Complete Phase 1 (Core Containerization)
- Begin Phase 2 (Enhanced Features)
- Set up GitHub repository

### Next Week
- Complete Phase 2
- Begin Phase 3 (Admin Interface)
- Begin Phase 4 (Cloud Deployment)

---

## Questions for User

1. **Deployment Preference**: 
   - Simple Compute Instance ($5-10/month)?
   - Or Kubernetes (more complex, higher cost)?

2. **Polling Frequency**:
   - Start with 30s safe default?
   - Or test at 10s current rate?

3. **Admin Interface Priority**:
   - Build web UI now (Phase 3)?
   - Or defer and use docker commands initially?

4. **TP-Link API Access**:
   - Do we have API documentation?
   - Known rate limits?
   - Any alternative APIs to consider?

5. **GOS Team Access**:
   - Who needs admin access?
   - Who needs read-only dashboard access?
   - VPN or public with auth?

---

## Resources

### Documentation Needed
- [ ] TP-Link Cloud API documentation
- [ ] Rate limits and quotas
- [ ] OAuth flow details
- [ ] Device capabilities

### External Resources
- [Original bentasker project](https://github.com/bentasker/tplink_to_influxdb)
- [InfluxDB Docker](https://hub.docker.com/_/influxdb)
- [Grafana Docker](https://hub.docker.com/r/grafana/grafana)
- [Akamai Linode Docs](https://www.linode.com/docs/)

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-02  
**Status**: Initial Planning Complete ✅


