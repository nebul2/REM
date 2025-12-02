# Implementation Roadmap - GOS Stats Migration

## Deployment Strategy (Confirmed)

### Phase 1: Local Development (Current)
- ✅ Project initialized
- ✅ Assessment complete
- 🔄 **In Progress**: Building Docker Compose stack
- ⏳ Test locally on Mac

### Phase 2: Staging (Pi400)
- Deploy Docker stack to pi400
- Replace native installation
- Use existing DNS: `stats.liveencode.com`
- Clean up original scripts/services

### Phase 3: Production (Future - After Staging Works)
- Deploy to Akamai Linode
- May use serverless + managed DB
- **Not starting this until staging is solid**

---

## Decisions Made

### Deployment Preference
✅ **Single Docker Compose stack** - Simple containerized deployment
- Not Kubernetes (too complex for now)
- Not separate production planning (staging first)

### Polling Frequency
✅ **Start with 30 seconds** - Make easily configurable
- Safer for API limits (unknown)
- Can adjust later based on testing
- Configurable via environment variable

### Admin UI
✅ **Defer for now** - Focus on core functionality first
- Can add later if needed
- For now: docker-compose commands are sufficient

### TP-Link API Documentation
⏳ **TBD** - Will test conservatively
- Start with 30s polling
- Monitor for rate limit errors
- Adjust based on real-world testing

### Access Control
⏳ **TBD** - Will set up basic auth initially
- Grafana: Basic authentication
- Can enhance later based on team needs

---

## Implementation Plan

### Step 1: Build Docker Stack (Current Task)
**Goal**: Single docker-compose.yml with 3 services

**Services**:
1. **Collector** (Python app)
   - Improved script (no hard-coded paths)
   - Environment variable configuration
   - Health check endpoint
   
2. **InfluxDB 2.x**
   - Persistent volume for data
   - Auto-initialize with org/bucket
   
3. **Grafana**
   - Pre-configured datasource
   - Persistent dashboards

**Ports** (Local DevBench allocation):
- 7001: Reserved for future admin UI
- 7002: InfluxDB (http://localhost:7002)
- 7003: Grafana (http://localhost:7003)

**Configuration**:
- Environment variables for all secrets
- Config file for non-sensitive settings
- Easy to customize per environment

### Step 2: Test Locally
**Actions**:
- Start docker-compose stack
- Verify collector runs
- Check data flows to InfluxDB
- Verify Grafana shows data
- Test token refresh
- Test restart/recovery

**Success Criteria**:
- All containers start without errors
- Data collection working
- Grafana dashboard functional
- Can pause/restart with docker commands

### Step 3: Prepare Pi400 Deployment
**Actions**:
- Copy docker-compose.yml to pi400
- Set up environment variables
- Backup existing InfluxDB data
- Test Docker installation on pi400
- Prepare migration script

**Pi400 Requirements**:
- Docker & Docker Compose installed
- Ports available (8086, 3000 currently in use)
- DNS: stats.liveencode.com → pi400

### Step 4: Deploy to Pi400 (Staging)
**Actions**:
- Stop native InfluxDB/Grafana services
- Start Docker stack on different ports temporarily
- Verify data collection works
- Migrate existing data to new InfluxDB
- Switch ports/update DNS if needed
- Monitor for 24-48 hours

**Success Criteria**:
- stats.liveencode.com shows Grafana
- Data collection continues seamlessly
- No data loss
- Original services stopped

### Step 5: Cleanup Pi400
**Actions**:
- Remove old Python scripts
- Remove cron jobs
- Remove native InfluxDB/Grafana (or keep for backup period)
- Clean up zombie processes
- Update documentation

### Step 6: Production Planning (Future)
**When**: After staging is stable
**Where**: Akamai Linode
**Options**:
- Single Docker container on Compute instance
- Serverless (Cloud Run equivalent) + managed DB
- Decision based on cost/requirements

---

## Technical Stack

### Docker Compose Structure
```yaml
version: '3.8'

services:
  collector:
    build: ./app
    environment:
      - POLL_INTERVAL=30
      - TPLINK_CLIENT_ID=...
      - TPLINK_CLIENT_SECRET=...
      - INFLUXDB_URL=http://influxdb:8086
    depends_on:
      - influxdb
    restart: unless-stopped

  influxdb:
    image: influxdb:2.7-alpine
    volumes:
      - influxdb-data:/var/lib/influxdb2
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_ORG=GOS
      - DOCKER_INFLUXDB_INIT_BUCKET=rem
    ports:
      - "7002:8086"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:10.4.2
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    ports:
      - "7003:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=...
    restart: unless-stopped

volumes:
  influxdb-data:
  grafana-data:
```

### File Structure
```
stats/
├── app/
│   ├── Dockerfile
│   ├── collector.py          # Improved main script
│   ├── requirements.txt
│   └── config/
│       └── config.yaml       # Default config
├── grafana/
│   └── provisioning/
│       ├── datasources/
│       └── dashboards/
├── docker-compose.yml
├── .env.example              # Template for secrets
├── .env                      # Actual secrets (gitignored)
└── README.md
```

---

## Configuration Management

### Environment Variables (.env file)
```bash
# TP-Link Cloud API
TPLINK_CLIENT_ID=fdcae128-0adf-4233-8a58-30760652bd16
TPLINK_CLIENT_SECRET=4087d4b9-5e0c-4e50-b06c-22580fc618d5
TPLINK_API_KEY=e71bf02f-8b71-42ee-8af0-62a7bdf6c866
TPLINK_REFRESH_TOKEN=<will get from pi400>

# InfluxDB
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_ORG=GOS
INFLUXDB_BUCKET=rem
INFLUXDB_TOKEN=<auto-generated or from pi400>

# Collector
POLL_INTERVAL=30
LOG_LEVEL=INFO
PERSIST_MODE=true

# Grafana
GRAFANA_ADMIN_PASSWORD=<auto-generated>
```

### Config File (config.yaml)
```yaml
poller:
  persist: true
  interval: 30  # Can be overridden by POLL_INTERVAL env var

influxdb:
  - name: "local"
    url: "http://influxdb:8086"
    org: "GOS"
    bucket: "rem"
    # Token from env var
```

---

## Port Allocation

### Local Development (Mac)
- 7001: Reserved (future admin UI)
- 7002: InfluxDB
- 7003: Grafana

### Staging (Pi400)
**Current Native Services**:
- 8086: InfluxDB (native)
- 3000: Grafana (native)

**Docker Stack Options**:
1. **Option A**: Use same ports, stop native services first
   - 8086: InfluxDB (Docker)
   - 3000: Grafana (Docker)
   
2. **Option B**: Use different ports, update later
   - 7002: InfluxDB (Docker)
   - 7003: Grafana (Docker)
   - Then switch after verification

**Recommendation**: Option B (safer migration)

### Production (Linode - Future)
- TBD - Will determine based on deployment method

---

## Migration Checklist

### Pre-Migration (Pi400)
- [ ] Backup InfluxDB data
- [ ] Document current configuration
- [ ] Note all device aliases
- [ ] Verify Docker installed on pi400
- [ ] Test Docker stack locally first

### Migration Day
- [ ] Stop native services (InfluxDB, Grafana)
- [ ] Stop cron job (comment out)
- [ ] Deploy Docker stack
- [ ] Verify data collection starts
- [ ] Import old data (if needed)
- [ ] Test Grafana access
- [ ] Monitor for errors

### Post-Migration
- [ ] Monitor for 24-48 hours
- [ ] Verify no data gaps
- [ ] Clean up old files
- [ ] Update documentation
- [ ] Remove zombie processes

---

## Testing Strategy

### Local Testing
1. **Start Stack**: `docker-compose up -d`
2. **Check Logs**: `docker-compose logs -f collector`
3. **Verify Data**: Check InfluxDB for new points
4. **Check Grafana**: Access http://localhost:7003
5. **Test Restart**: `docker-compose restart collector`
6. **Test Stop/Start**: Full cycle

### Staging Testing (Pi400)
1. Deploy to pi400
2. Run in parallel with native (different ports)
3. Compare data from both sources
4. Verify collector stability
5. Check resource usage
6. Monitor for 48 hours

### Success Criteria
- ✅ No errors in logs
- ✅ Data appears in InfluxDB
- ✅ Grafana shows data
- ✅ Token refresh works
- ✅ Can restart without issues
- ✅ Resource usage reasonable

---

## Timeline Estimate

### Week 1 (Current)
- **Day 1-2**: Build Docker stack, improve Python collector
- **Day 3-4**: Test locally, fix issues
- **Day 5**: Prepare pi400 deployment files

### Week 2
- **Day 1**: Deploy to pi400, initial testing
- **Day 2-3**: Monitor, fix any issues
- **Day 4-5**: Migrate data, switch to production ports
- **Weekend**: Extended monitoring

### Week 3
- **Day 1-2**: Cleanup pi400 (if all good)
- **Day 3-5**: Enhance Grafana dashboards
- **End of week**: Staging complete ✅

---

## Known Challenges

### 1. Pi400 Architecture
- ARM64 architecture - need to build for ARM or use multi-arch
- **Solution**: Use official ARM images or build multi-arch

### 2. Port Conflicts
- Native services use 8086, 3000
- **Solution**: Use different ports initially, switch after migration

### 3. Token Migration
- Refresh token stored in file on pi400
- **Solution**: Extract token, set as environment variable

### 4. Data Migration
- Existing InfluxDB data needs to be preserved
- **Solution**: Backup before migration, import to new instance

### 5. DNS/Reverse Proxy
- stats.liveencode.com may need nginx/traefik config
- **Solution**: Check existing setup, may need proxy config

---

## Next Actions (Immediate)

1. ✅ Create docker-compose.yml
2. ✅ Improve Python collector (remove hard-coded paths)
3. ✅ Create Dockerfile for collector
4. ✅ Set up Grafana provisioning
5. ✅ Create .env.example template
6. ⏳ Test locally
7. ⏳ Prepare pi400 deployment instructions

---

**Last Updated**: 2025-12-02  
**Status**: Ready to start implementation  
**Priority**: Build Docker stack now, test locally, then deploy to pi400

