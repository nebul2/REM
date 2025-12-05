# GOS Remote Energy Measurement (REM) System

**Status**: ✅ **Operational** - Fully containerized and deployed

A Docker-based system for collecting real-time power consumption data from TP-Link Tapo P110 smart plugs distributed globally, storing in TimescaleDB, and exploring through the GOS REM Data Exploration Tool.

---

## Quick Links

- **[Project Plan](PROJECT_PLAN.md)** - Detailed implementation plan and architecture
- **[Current Assessment](CURRENT_ASSESSMENT.md)** - Analysis of existing Pi400 setup
- **[DevBench Dashboard](http://localhost:8888)** - Project management

---

## What This Does

The Greening of Streaming (GOS) organization uses this system to:

1. **Collect** real-time power measurements from Tapo P110 wireless smart plugs
2. **Store** time-series data in TimescaleDB (PostgreSQL extension)
3. **Explore** data through the interactive GOS REM Data Exploration Tool
4. **Analyze** energy usage during streaming experiments with advanced filtering, grouping, and statistical analysis

### Use Cases
- **Remote Energy Measurement (REM)**: Monitor power consumption of computers/equipment globally
- **Streaming Experiments**: Measure energy impact of different streaming configurations
- **Cost Analysis**: Calculate energy costs across different compute loads
- **Sustainability Research**: Support GOS's mission of understanding streaming energy consumption

---

## Project Status

### Current State
- ✅ **Fully Containerized**: Docker Compose stack running on Pi400
- ✅ **TimescaleDB**: PostgreSQL-based time-series database
- ✅ **Data Collector**: Polling TP-Link API every 30 seconds
- ✅ **GOS REM Data Exploration Tool**: Interactive web UI for data analysis
- ✅ **Collector Control**: Web-based start/stop/pause and polling interval control
- ✅ **Experiment Management**: Device grouping and A/B testing support
- ✅ **Snapshot Gallery**: Save and archive chart snapshots with annotations

### Key Features
- 📊 **Interactive Charts**: Overlay multiple experiments, toggle device visibility, statistical overlays
- 🔬 **Experiment Groups**: Create device groups for A/B testing and comparisons
- 📈 **Statistical Analysis**: Mean, median, total, and average calculations with legend-based filtering
- 📸 **Snapshot Archive**: Save chart snapshots with annotations for future reference
- ⏱️ **Dynamic Time Ranges**: Zoom, pan, and select time ranges for detailed analysis
- 🎨 **GoS Branding**: Consistent branding with Greening of Streaming logo and colors

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │  Data Collector │  │   TimescaleDB    │  │  Admin UI    │ │
│  │   (Python)      │──│  (PostgreSQL)    │──│ (FastAPI)    │ │
│  └─────────────────┘  └──────────────────┘  └──────────────┘ │
│                                │                              │
│                                └──────────────┬───────────────┘
│                                               │
│                                    ┌──────────────────┐
│                                    │  Data Exploration│
│                                    │      Tool        │
│                                    └──────────────────┘
└───────────────────────────────┬───────────────────────────────┘
                                │
                    ┌───────────────────────┐
                    │  TP-Link Cloud API    │
                    │  (Tapo P110 Devices)  │
                    └───────────────────────┘
```

### Components
1. **Python Data Collector**: Polls TP-Link Cloud API, collects power readings from all P110 devices
2. **TimescaleDB**: PostgreSQL-based time-series database for storing measurements
3. **Admin UI (FastAPI)**: Web interface for system management and data exploration
4. **GOS REM Data Exploration Tool**: Interactive charts, experiment grouping, snapshot gallery

---

## Prerequisites

- Docker & Docker Compose
- TP-Link Cloud API credentials (client ID, secret)
- OAuth authorization code (obtained via browser)
- Tapo P110 smart plugs registered to TP-Link account

---

## Quick Start

**👉 For the simplest deployment instructions, see [DEPLOYMENT_SIMPLE.md](DEPLOYMENT_SIMPLE.md)**

```bash
# Clone repository
git clone git@github.com:dom-robinson/stats.git
cd stats

# Configure (see DEPLOYMENT_SIMPLE.md for details)
cp ENV_TEMPLATE .env
# Edit .env with your credentials

# Start everything
docker-compose up -d

# Wait 30 seconds, then access:
# - Data Exploration Tool: http://localhost:7001
# - Manage Groups: http://localhost:7001/manage
# - Snapshot Gallery: http://localhost:7001/gallery
```

---

## Configuration

### Environment Variables
```bash
# TP-Link Cloud API
TPLINK_CLIENT_ID=your-client-id
TPLINK_CLIENT_SECRET=your-secret
TPLINK_REFRESH_TOKEN=initial-token

# PostgreSQL/TimescaleDB
POSTGRES_HOST=timescaledb
POSTGRES_PORT=5432
POSTGRES_DB=gos_rem
POSTGRES_USER=gos
POSTGRES_PASSWORD=your-secure-password

# Collector
POLL_INTERVAL=30  # seconds (configurable via UI)
LOG_LEVEL=INFO
```

### Polling Frequency
- **Current**: 10 seconds (Pi400)
- **Recommended**: 30 seconds (safer for API limits)
- **Range**: 10-300 seconds

---

## Data Model

### TimescaleDB Schema
```sql
CREATE TABLE gos_rem (
    time TIMESTAMPTZ NOT NULL,
    alias TEXT NOT NULL,
    power_watts FLOAT NOT NULL
);

SELECT create_hypertable('gos_rem', 'time');
```

### Example Query (SQL)
```sql
SELECT time_bucket('1 minute', time) AS time,
       alias,
       AVG(power_watts) AS avg_power
FROM gos_rem
WHERE time > NOW() - INTERVAL '1 hour'
  AND alias = 'London-Office-PC'
GROUP BY time_bucket('1 minute', time), alias
ORDER BY time;
```

---

## GOS REM Data Exploration Tool

### Features
- **Interactive Charts**: Overlay multiple experiments with smooth curves and zoom/pan
- **Device Grouping**: Create experiment groups (A/B testing support)
- **Statistical Analysis**: Mean, median, total, and average with dynamic recalculation
- **Legend-based Filtering**: Show/hide devices and recalculate statistics
- **Time Range Selection**: Zoom and pan to focus on specific time periods
- **Annotation System**: Add timeline markers with notes
- **Snapshot Gallery**: Save, archive, and search historical charts
- **Collector Control**: Start/stop polling and adjust polling frequency via UI

---

## Deployment Targets

### Local Development
```bash
# Default ports
7001: Admin UI / Data Exploration Tool
5432: TimescaleDB (PostgreSQL)
```

### Akamai Linode (Production)
- **Instance**: Nanode 1GB ($5/month)
- **Region**: Closest to team
- **Access**: HTTPS with Let's Encrypt SSL
- **Backup**: Daily automated backups

### Production Deployment (Pi400)
- **Status**: ✅ Currently running on Raspberry Pi 400
- **URL**: https://stats.liveencode.com
- **Access**: Protected by Authelia authentication
- **Services**: All services running in Docker containers

---

## API Details

### TP-Link Cloud API
- **Base URL**: `https://aps1-openapi.tplinknbu.com/v1/`
- **Authentication**: OAuth 2.0
- **Rate Limits**: Unknown (being conservative)
- **Devices Supported**: Tapo P110, P110M

### Endpoints Used
1. `/oauth/token` - Get/refresh access token
2. `/getDeviceList` - List all devices
3. `/device/deviceControl` - Get real-time power

---

## Development

### Project Structure
```
stats/
├── app/
│   ├── collector.py       # Main data collector (polls TP-Link API)
│   ├── config/            # Configuration files
│   └── Dockerfile         # Collector container
├── admin/                 # Admin web UI and Data Exploration Tool
│   ├── app.py            # FastAPI backend
│   ├── templates/        # HTML templates
│   ├── static/           # CSS, JavaScript, images
│   └── Dockerfile        # Admin UI container
├── scripts/              # Database initialization scripts
├── docker-compose.yml    # Full stack orchestration
├── ENV_TEMPLATE          # Environment variables template
└── README.md
```

### Running Tests
```bash
# Unit tests
pytest tests/

# Integration test (requires API credentials)
pytest tests/integration/

# Load test
python tests/load_test.py
```

---

## Migration from Pi400

### Backup Current Data
```bash
# SSH to Pi400
ssh pi400

# Backup InfluxDB
influx backup /tmp/influx-backup \
  -t gwTu1qAtPgIRU8eWNpLXuz92pKo6_lgV7Y4mhdMM7n_XOe-fTXts7T54P_FQJ69UMVuTyhr77Ly7XCGz9QUNAA==

# Copy to local
scp -r pi400:/tmp/influx-backup ./backup/
```

### Restore to Container
```bash
# Start stack
docker-compose up -d

# Restore data
docker cp ./backup/ stats-influxdb:/backup/
docker exec stats-influxdb influx restore /backup/
```

---

## Troubleshooting

### Collector Not Starting
```bash
# Check logs
docker-compose logs collector

# Common issues:
# - Missing refresh token
# - Invalid credentials
# - API rate limit
```

### No Data in Charts
```bash
# Check collector is writing
docker-compose logs collector | grep "Wrote"

# Check TimescaleDB
docker exec stats-timescaledb psql -U gos -d gos_rem -c \
  "SELECT COUNT(*), MAX(time) FROM gos_rem WHERE time > NOW() - INTERVAL '1 hour';"
```

### Token Refresh Failed
```bash
# Get new authorization code from browser
# Update .env with new code
# Restart collector
docker-compose restart collector
```

---

## Contributing

This project is part of the Greening of Streaming organization's research initiative.

### Development Setup
1. Fork the repository
2. Create feature branch
3. Make changes
4. Test locally
5. Submit pull request

### Code Style
- Python: PEP 8
- Docstrings: Google style
- Type hints: Required for public functions

---

## Roadmap

### Phase 1: Core Migration (Week 1)
- [x] Assess current Pi400 setup
- [x] Create project plan
- [ ] Improve Python collector
- [ ] Create Docker Compose stack
- [ ] Test local deployment

### Phase 2: Enhanced Features (Week 2)
- [ ] Advanced Grafana dashboards
- [ ] Configurable polling
- [ ] Data retention policies
- [ ] Backup automation

### Phase 3: Cloud Deployment (Week 3)
- [ ] Deploy to Akamai Linode
- [ ] Set up monitoring
- [ ] SSL/TLS configuration
- [ ] Team access setup

### Phase 4: Admin Interface (Week 4)
- [ ] Web-based control panel
- [ ] Start/stop/pause controls
- [ ] Device management
- [ ] Log viewer

---

## Cost Estimation

### Self-Hosted (Linode)
- Compute: $5/month (Nanode 1GB)
- Backup: $2/month
- **Total**: ~$7/month

### Cloud Services
- InfluxDB Cloud: $0-50/month
- Grafana Cloud: $0-49/month
- Cloud Run: $0-5/month
- **Total**: $0-100/month

**Recommendation**: Self-hosted for cost control

---

## Security

### Secrets Management
- OAuth credentials in environment variables
- InfluxDB token in Docker secrets
- Grafana admin password auto-generated
- No secrets in Git repository

### Network Security
- InfluxDB not exposed publicly
- Grafana behind authentication
- Admin UI (when built) behind auth
- HTTPS for public interfaces

---

## Resources

### Documentation
- [TP-Link Cloud API](https://www.tp-link.com/uk/support/download/tapo-p110/)
- [InfluxDB 2.x Docs](https://docs.influxdata.com/influxdb/v2/)
- [Grafana Docs](https://grafana.com/docs/)

### Related Projects
- [bentasker/tplink_to_influxdb](https://github.com/bentasker/tplink_to_influxdb) - Original inspiration
- [Greening of Streaming](https://www.greeningofstreaming.org) - Organization

---

## Support

### Issues
Report issues on GitHub Issues page

### Contact
- **Project Lead**: Dom Robinson
- **Organization**: Greening of Streaming
- **Email**: d2@d2consulting.co.uk

---

## License

TBD - To be determined with GOS team

---

**Last Updated**: 2025-12-05  
**Version**: 1.0.0  
**Status**: Operational and Deployed


