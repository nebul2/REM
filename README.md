# GOS Remote Energy Measurement (REM) System

**Status**: 🚧 Under Development - Migrating from Pi400 to containerized deployment

A Docker-based system for collecting real-time power consumption data from TP-Link Tapo P110 smart plugs distributed globally, storing in InfluxDB, and visualizing through Grafana dashboards.

---

## Quick Links

- **[Project Plan](PROJECT_PLAN.md)** - Detailed implementation plan and architecture
- **[Current Assessment](CURRENT_ASSESSMENT.md)** - Analysis of existing Pi400 setup
- **[DevBench Dashboard](http://localhost:8888)** - Project management

---

## What This Does

The Greening of Streaming (GOS) organization uses this system to:

1. **Collect** real-time power measurements from Tapo P110 wireless smart plugs
2. **Store** time-series data in InfluxDB
3. **Visualize** power consumption in Grafana dashboards
4. **Analyze** energy usage during streaming experiments

### Use Cases
- **Remote Energy Measurement (REM)**: Monitor power consumption of computers/equipment globally
- **Streaming Experiments**: Measure energy impact of different streaming configurations
- **Cost Analysis**: Calculate energy costs across different compute loads
- **Sustainability Research**: Support GOS's mission of understanding streaming energy consumption

---

## Project Status

### Current State (Pi400)
- ✅ Running on Raspberry Pi 400
- ✅ InfluxDB + Grafana operational
- ✅ Python collector working
- ⚠️ Multiple zombie processes (needs cleanup)
- ⚠️ Hard-coded paths (not portable)

### Migration Goals
- 🎯 **Containerized**: Docker Compose stack
- 🎯 **Portable**: Deploy anywhere (Linode, AWS, GCP, etc.)
- 🎯 **Configurable**: Easy to adjust polling, add devices
- 🎯 **Maintainable**: Admin interface for start/stop/pause
- 🎯 **Scalable**: Support growing device count

### Development Progress
- [x] Phase 1: Assessment & Planning
- [ ] Phase 2: Core Containerization
- [ ] Phase 3: Enhanced Features
- [ ] Phase 4: Admin Interface
- [ ] Phase 5: Cloud Deployment

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │  Data Collector │  │   InfluxDB 2.x  │  │  Grafana    │ │
│  │   (Python)      │──│   (Database)    │──│ (Dashboard) │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│                                                               │
└───────────────────────────────┬───────────────────────────────┘
                                │
                    ┌───────────────────────┐
                    │  TP-Link Cloud API    │
                    │  (Tapo P110 Devices)  │
                    └───────────────────────┘
```

### Components
1. **Python Data Collector**: Polls TP-Link Cloud API, collects power readings
2. **InfluxDB 2.x**: Time-series database for storing measurements
3. **Grafana**: Dashboard for visualization and analysis
4. **Admin UI** (planned): Web interface for system management

---

## Prerequisites

- Docker & Docker Compose
- TP-Link Cloud API credentials (client ID, secret)
- OAuth authorization code (obtained via browser)
- Tapo P110 smart plugs registered to TP-Link account

---

## Quick Start (Coming Soon)

```bash
# Clone repository
git clone git@github.com:dom-robinson/stats.git
cd stats

# Configure
cp .env.example .env
# Edit .env with your credentials

# Start services
docker-compose up -d

# View logs
docker-compose logs -f collector

# Access Grafana
open http://localhost:7003
```

---

## Configuration

### Environment Variables
```bash
# TP-Link Cloud API
TPLINK_CLIENT_ID=your-client-id
TPLINK_CLIENT_SECRET=your-secret
TPLINK_REFRESH_TOKEN=initial-token

# InfluxDB
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_ORG=GOS
INFLUXDB_BUCKET=rem
INFLUXDB_TOKEN=your-token

# Collector
POLL_INTERVAL=30  # seconds
PERSIST_MODE=true
LOG_LEVEL=INFO
```

### Polling Frequency
- **Current**: 10 seconds (Pi400)
- **Recommended**: 30 seconds (safer for API limits)
- **Range**: 10-300 seconds

---

## Data Model

### InfluxDB Schema
```
Measurement: gos_rem
Tags:
  - alias: Device location/name
Fields:
  - powerWatts: Current power consumption (float)
Timestamp: Nanosecond precision
```

### Example Query (Flux)
```flux
from(bucket: "rem")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "gos_rem")
  |> filter(fn: (r) => r.alias == "London-Office-PC")
```

---

## Grafana Dashboards (Planned)

### Features
- **Device Filtering**: Multi-select specific devices
- **Time Range**: Compare different time periods
- **Energy Totals**: Calculate kWh consumed
- **Real-time Updates**: Live data streaming
- **Cost Estimation**: Based on configurable rates
- **Experiment Mode**: Tag and compare experiment runs

---

## Deployment Targets

### Local Development
```bash
# DevBench ports
7001: Admin UI
7002: InfluxDB
7003: Grafana
```

### Akamai Linode (Production)
- **Instance**: Nanode 1GB ($5/month)
- **Region**: Closest to team
- **Access**: HTTPS with Let's Encrypt SSL
- **Backup**: Daily automated backups

### Alternative: Google Cloud Run
Similar to RAMS/Meetex architecture:
- Cloud Run for collector (scheduled)
- Cloud SQL or InfluxDB Cloud
- Grafana Cloud (free tier)

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

### Project Structure (Planned)
```
stats/
├── app/
│   ├── collector.py       # Main data collector
│   ├── config.py          # Configuration management
│   ├── tplink_api.py      # TP-Link API client
│   └── influx_writer.py   # InfluxDB writer
├── admin/                 # Admin web UI
├── grafana/
│   └── dashboards/        # Dashboard definitions
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── config.example.yaml
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

### No Data in Grafana
```bash
# Check collector is writing
docker-compose logs collector | grep "Wrote"

# Check InfluxDB
docker exec stats-influxdb influx query \
  'from(bucket:"rem") |> range(start:-1h) |> count()'
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

**Last Updated**: 2025-12-02  
**Version**: 0.1.0-alpha  
**Status**: Under Active Development


