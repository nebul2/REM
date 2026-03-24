# GOS Remote Energy Measurement (REM) System

**Status**: ✅ **Operational** - Fully containerized and deployed

A Docker-based system for collecting real-time power consumption data from TP-Link Tapo P110 smart plugs distributed globally, storing in TimescaleDB, and exploring through the GOS REM Data Exploration Tool.

---

## Quick Links

- **[Simple Deployment Guide](#simple-deployment-guide)** - Step-by-step setup for non-technical users
- **[User Guide](docs/USER_GUIDE.md)** - Complete guide to using the GOS REM Data Exploration Tool
- **[Changelog](docs/CHANGELOG.md)** - Version history and release notes
- **[Documentation](docs/)** - All development notes and detailed guides

---

## Simple Deployment Guide

**For non-technical users - Get the system running in under 10 minutes!**

### Prerequisites
You'll need:
- A computer with **Docker Desktop** installed ([Download here](https://www.docker.com/products/docker-desktop))
- Your **TP-Link Cloud API credentials** (Client ID, Client Secret, and Refresh Token)
- About 10 minutes

### Step 1: Install Docker
1. Download and install **Docker Desktop** from [docker.com](https://www.docker.com/products/docker-desktop)
2. Open Docker Desktop and make sure it's running (you'll see a Docker icon in your system tray)

### Step 2: Get the Code
1. Open a terminal/command prompt
2. Run:
   ```bash
   git clone git@github.com:dom-robinson/stats.git
   cd stats
   ```
   (Or download the ZIP file from GitHub and extract it, then open a terminal in that folder)

### Step 3: Configure
1. Copy the template file:
   ```bash
   cp ENV_TEMPLATE .env
   ```

2. Open the `.env` file in a text editor and fill in your TP-Link credentials:
   ```
   TPLINK_CLIENT_ID=your-client-id-here
   TPLINK_CLIENT_SECRET=your-secret-here
   TPLINK_REFRESH_TOKEN=your-refresh-token-here
   POSTGRES_PASSWORD=choose-a-secure-password
   ```

### Step 4: Start Everything
Run this command:
```bash
docker-compose up -d
```

Wait about 30 seconds, then check if everything started:
```bash
docker-compose ps
```

All services should show "Up" status.

### Step 5: Access the System
Open your web browser and go to:
- **Main Interface**: http://localhost:7001

### Step 6: View Your Data
1. The system will automatically start collecting data from your TP-Link devices
2. Click "Exploration" in the top menu to see charts
3. Click "Groups" to organize your devices into experiment groups
4. Data will start appearing within 30 seconds

### Stopping the System
To stop everything:
```bash
docker-compose down
```

To stop but keep your data:
```bash
docker-compose stop
```

### Need Help?
- Check the logs: `docker-compose logs collector`
- See [Troubleshooting](#troubleshooting) section below
- Check the [detailed deployment guide](docs/DEPLOYMENT_SIMPLE.md)

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
- ✅ **Fully Containerized**: Docker Compose stack for collector, TimescaleDB, and admin UI
- ✅ **TimescaleDB**: PostgreSQL-based time-series database
- ✅ **Data Collector**: Polling TP-Link API every 30 seconds
- ✅ **GOS REM Data Exploration Tool**: Interactive web UI for data analysis
- ✅ **Collector Control**: Web-based start/stop/pause and polling interval control
- ✅ **Experiment Management**: Device grouping and A/B testing support
- ✅ **Snapshot Gallery**: Save and archive chart snapshots with annotations
- ✅ **Database Export/Import**: Full backup and migration capabilities
- ✅ **Production Deployment**: Primary instance running on Akamai Linode (`rem.greeningofstreaming.org`)
- ✅ **Pi400 Dev/Staging**: Original Pi400 stack retained as development and backup environment

### Key Features
- 📊 **Interactive Charts**: Overlay multiple experiments, toggle device visibility, statistical overlays
- 🔬 **Experiment Groups**: Create device groups for A/B testing and comparisons
- 📈 **Statistical Analysis**: Mean, median, total, and average calculations with legend-based filtering
- 📸 **Snapshot Archive**: Save chart snapshots with annotations and download as ZIP (image + CSV + metadata)
- ⏱️ **Dynamic Time Ranges**: Zoom, pan (xy mode), and select time ranges for detailed analysis
- 🖱️ **Grafana-like Selection**: Single-click to select only one device, shift-click to toggle multiple devices
- 💾 **Data Export/Import**: Full database backup and migration support (ZIP format)
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

## Quick Start (For Developers)

See [Simple Deployment Guide](#simple-deployment-guide) above for step-by-step instructions.

For developers familiar with Docker:

```bash
git clone git@github.com:dom-robinson/stats.git
cd stats
cp ENV_TEMPLATE .env
# Edit .env with your credentials
docker-compose up -d
```

Access:
- **Data Exploration Tool**: http://localhost:7001
- **Manage Groups**: http://localhost:7001/manage
- **Snapshot Gallery**: http://localhost:7001/gallery
- **Admin (Export/Import)**: http://localhost:7001/admin

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

# Admin UI Basic Auth (optional, recommended for production)
ADMIN_BASIC_USER=your-admin-username
ADMIN_BASIC_PASSWORD=your-strong-password
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
- **Database Export/Import**: Full backup and migration support for all data, experiments, groups, and snapshots

---

## Deployment Targets

### Local Development
```bash
# Default ports
7001: Admin UI / Data Exploration Tool
5432: TimescaleDB (PostgreSQL)
```

### Akamai Linode (Production)
- **Role**: Primary production deployment
- **Instance**: Nanode 1GB ($5/month)
- **Region**: Closest to team
- **Access**: `https://rem.greeningofstreaming.org` (Caddy + Let's Encrypt)
- **Auth**: HTTP Basic Auth via admin middleware (`ADMIN_BASIC_USER` / `ADMIN_BASIC_PASSWORD`)

### Pi400 Deployment (Dev / Staging)
- **Status**: ✅ Raspberry Pi 400, used for development and staging
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

## Data Backup & Migration

### Using the Admin Interface (Recommended)

The easiest way to backup or migrate your data is through the web interface:

1. Navigate to **Admin** in the menu (http://localhost:7001/admin)
2. Click **Export Database** to download a complete backup ZIP file
3. To restore, select the ZIP file and click **Import Database**

The export includes:
- All TimescaleDB power measurement data
- All experiments and configurations
- All device groups
- All snapshots (images and metadata)
- All annotations

### Manual Backup (Advanced)

For manual backups using `pg_dump`:

```bash
# Export database
docker exec stats-timescaledb pg_dump -U gos gos_rem > backup_$(date +%Y%m%d).sql

# Copy JSON files
cp admin/data/device_groups.json backup/
cp admin/data/experiments.json backup/
cp admin/data/snapshots.json backup/
cp -r admin/data/snapshots/ backup/
```

### Restore Manual Backup

```bash
# Restore database
cat backup_*.sql | docker exec -i stats-timescaledb psql -U gos gos_rem

# Restore JSON files
cp backup/*.json admin/data/
cp -r backup/snapshots/* admin/data/snapshots/
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
- [x] Configurable polling
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
- TimescaleDB Cloud: $0-50/month
- Cloud Run: $0-5/month
- **Total**: $0-55/month

**Recommendation**: Self-hosted for cost control

---

## Security

### Secrets Management
- OAuth credentials in environment variables
- PostgreSQL/TimescaleDB password in environment variables
- No secrets in Git repository

### Network Security
- TimescaleDB not exposed publicly
- Admin UI behind authentication:
  - **Production (Linode)**: Built-in HTTP Basic Auth + Caddy HTTPS
  - **Dev (Pi400)**: Traefik/Authelia in front of the admin UI
- HTTPS for public interfaces

---

## Resources

### Documentation
- [TP-Link Cloud API](https://www.tp-link.com/uk/support/download/tapo-p110/)
- [TimescaleDB Docs](https://docs.timescale.com/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)

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

**Last Updated**: 2026-03-24  
**Version**: 1.4.3  
**Status**: ✅ Operational – Production on Linode, Pi400 as dev/staging  
**Documentation**: All development notes and guides are in the [`docs/`](docs/) folder

---

## Release Notes

### v1.4.3 (Hotfix: Starlette 1.x templates - 2026-03-24)

**Fixed**
- **500 / Internal Server Error** on all HTML pages after dependency upgrades: Starlette 1.x requires `Jinja2Templates.TemplateResponse(request, name, context)` instead of `(name, context)`. All admin page renders were updated accordingly.

### v1.4.2 (Experiment full data export & UX - 2026-03-24)

**What's New**
- **Experiment “Download all data”** — ZIP export of every stored power reading (one row per collector poll) for the experiment time range and devices from linked groups, plus `experiment_metadata.json`, `annotations.json`, and `README_export.txt` explaining the difference vs chart aggregation.
- **API** — `GET /api/experiments/{experiment_id}/export` returns that ZIP (same auth rules as the rest of the admin UI).
- **Routing** — `GET /experiment` redirects to `/experiments` (307) for common bookmark typos.
- **Copy** — Experiments and Exploration pages clarify that Exploration charts use aggregated series; this export is full-resolution history.

See [`docs/CHANGELOG.md`](docs/CHANGELOG.md) for the full changelog.

### v1.4.1 (Collector token recovery - 2026-03-23)

**Fixed**
- Collector no longer stalls silently when the TP-Link cloud returns **token invalid** (`-10902`): it refreshes the OAuth token and retries the polling cycle, and prefers the persisted rotating refresh token on disk.

### v1.4.0 (Initial Linode Production Release - 2026-03-11)

**What's New**
- ✅ First production deployment on Akamai Linode (`rem.greeningofstreaming.org`)
- ✅ Built‑in HTTP Basic Auth in the admin UI, controlled via `ADMIN_BASIC_USER` / `ADMIN_BASIC_PASSWORD`
- ✅ Caddy reverse proxy on Linode for HTTPS termination (Let's Encrypt) and HTTP→HTTPS redirects
- ✅ End‑to‑end data migration from Pi400 to Linode TimescaleDB (historic + live data)
- ✅ Documented disaster‑recovery path from GitHub + DB backup

---

### v1.3.2 (2025-12-17)

**Cleanup Release** - Removed unused services:
- Removed Grafana (replaced by custom admin UI)
- Removed InfluxDB (migrated to TimescaleDB)
- Freed ~6GB disk space on production server

### v1.3.1 (2025-12-17)

**Stability Update** - API rate limiting fix:
- Added configurable Device Query Delay setting in UI
- Prevents TP-Link API rate limiting (429 errors)
- Fixed collector hanging after rate limit errors

### v1.3.0 (2025-12-13)

**User Feedback Release** - Based on feedback from Ben:
- Added horizontal scrollbar for zoomed charts
- Snapshot ZIP downloads now include CSV data export
- Improved chart navigation and data export capabilities

### v1.2.0 (2025-12-12)

#### What's New
- ✅ **Database Export/Import**: Full backup and migration support - export all data, experiments, groups, and snapshots as ZIP
- ✅ **Grafana-like Device Selection**: Single-click legend to select one device, shift-click to toggle multiple devices
- ✅ **Snapshot ZIP Downloads**: Download snapshots as ZIP containing image, CSV data, and metadata
- ✅ **Chart B Statistical Overlays**: Statistical overlays now work correctly in split chart mode
- ✅ **Experiment Reactivation**: Clear end dates to reactivate "current" experiments
- ✅ **Improved Pan/Zoom**: Click and drag to pan in both horizontal and vertical directions
- ✅ **Gallery Layout Fixes**: Better handling of long experiment details in snapshot gallery

#### Bug Fixes
- Fixed Chart B statistical overlays not working in split mode
- Fixed gallery download button not working
- Fixed gallery layout breaking with long experiment details
- Fixed experiment reactivation (clearing end dates)
- Fixed pan mode (now supports both x and y axes)
- Fixed alert spam during auto-refresh failures

#### Technical Improvements
- Added export/import endpoints with pg_dump/CSV fallback support
- Improved error handling for consecutive API failures
- Enhanced UI with progress indicators for export/import
- Better validation and user feedback for destructive operations

---

### v1.1.0 (2025-12-08)

#### What's New
- ✅ **Improved Error Handling**: Better timeout management and error messages for large queries
- ✅ **Smart Aggregation**: Automatic interval adjustment based on time range and device count
- ✅ **Query Optimization**: Faster queries for large datasets (>50k points)
- ✅ **Enhanced Time Range**: Added 7-day and 30-day lookback options
- ✅ **Live Updates**: Auto-refreshing charts with pause/resume controls
- ✅ **Fixed Time Range & Aggregation**: Dropdowns now properly reload charts
- ✅ **Better Error Messages**: Clear feedback for timeouts and API errors

#### Bug Fixes
- Fixed 502/504 timeout errors for large time ranges
- Fixed time range dropdown not updating charts
- Fixed aggregation dropdown not applying changes
- Fixed JSON parsing errors on failed requests
- Fixed MutationObserver errors in Chart.js
- Fixed database password configuration issues

#### Technical Improvements
- Added 5-minute query timeout handling
- Optimized time bucket generation for large datasets
- Improved fetch error handling with proper JSON parsing
- Added request abort controllers for timeout management

---

### v1.0.0 (Initial Release - 2025-12-06)

#### What's New
- ✅ Complete Docker-based containerization
- ✅ Migration from InfluxDB to TimescaleDB (PostgreSQL extension)
- ✅ GOS REM Data Exploration Tool with interactive charts
- ✅ Experiment management system with device grouping
- ✅ Snapshot gallery with annotations
- ✅ Collector control via web UI (start/stop/polling frequency)
- ✅ Default chart loading with all devices
- ✅ Full GoS branding with logo and colors

#### Migration Notes
- Legacy InfluxDB data can be migrated using forward-fill script
- Old native InfluxDB/Grafana installation on Pi400 has been decommissioned


