# Standalone Deployment Guide

This system is designed to run as a **standalone Docker Compose stack** that works out of the box without any external dependencies.

## ✅ What Works Out of the Box

- **TimescaleDB**: Automatically initializes schema on first run
- **Data Collector**: Starts polling TP-Link API immediately after database is ready
- **Admin UI**: Accessible via HTTP on configured port (default: 7001)
- **Grafana**: Optional, accessible via HTTP on configured port (default: 7003)

## Quick Start

```bash
# 1. Clone repository
git clone git@github.com:dom-robinson/stats.git
cd stats

# 2. Configure environment
cp ENV_TEMPLATE .env
# Edit .env with your TP-Link credentials

# 3. Start everything
docker-compose up -d

# 4. Access the system
# Admin UI: http://localhost:7001
# Grafana: http://localhost:7003
```

## Requirements

- Docker & Docker Compose
- TP-Link Cloud API credentials (Client ID, Secret, Refresh Token)
- Ports available: 7001 (Admin UI), 7003 (Grafana, optional), 5432 (TimescaleDB)

## What Gets Started Automatically

1. **TimescaleDB**: Database with schema auto-initialized
2. **Collector**: Python service that polls TP-Link API every 30 seconds
3. **Admin UI**: FastAPI web application with Data Exploration Tool
4. **Grafana** (optional): Visualization dashboard

## Access Points

All services are accessible via HTTP on the Docker host:

- `http://localhost:7001` - Admin UI / Data Exploration Tool
- `http://localhost:7003` - Grafana (optional)
- `http://localhost:5432` - TimescaleDB (PostgreSQL - internal use)

To access from other machines, replace `localhost` with the Docker host's IP address.

## No External Dependencies

- ✅ **No Traefik required** - Services exposed directly via Docker port mapping
- ✅ **No external networks** - All services use internal Docker network
- ✅ **No reverse proxy needed** - Direct HTTP access works fine
- ✅ **No SSL certificates required** - HTTP access is sufficient for local/private networks

## Behind a Reverse Proxy (Optional)

If you want to run this behind Traefik, nginx, or another reverse proxy:

1. Keep the Traefik labels commented out in `docker-compose.yml` (they're already removed)
2. Configure your reverse proxy to forward requests to `http://localhost:7001`
3. Add SSL/TLS at the reverse proxy level

## Configuration

All configuration is done via the `.env` file. See [ENV_TEMPLATE](ENV_TEMPLATE) for all available options.

Key settings:
- `ADMIN_PORT=7001` - Port for Admin UI
- `GRAFANA_PORT=7003` - Port for Grafana
- `POSTGRES_PASSWORD=...` - Database password
- `TPLINK_REFRESH_TOKEN=...` - Your TP-Link API refresh token

## Data Persistence

All data is stored in Docker volumes:
- `timescaledb-data` - Database files
- `collector-data` - Token files
- `admin-data` - Groups, snapshots, annotations
- `grafana-data` - Grafana dashboards and settings

Data persists across container restarts. To remove all data:
```bash
docker-compose down -v
```

## Verification

After starting, verify everything is working:

```bash
# Check all services are running
docker-compose ps

# Check collector is polling
docker-compose logs collector | grep "Wrote"

# Check admin UI is responding
curl http://localhost:7001/api/devices
```

## Troubleshooting

See [DEPLOYMENT_SIMPLE.md](DEPLOYMENT_SIMPLE.md) for detailed troubleshooting.

For more information, see [README.md](README.md).

