# GOS REM - Simple Deployment Guide

## What You Need

- A computer with Docker and Docker Compose installed
- Your TP-Link Cloud API credentials (Client ID, Client Secret, Refresh Token)
- About 10 minutes

## Step 1: Get the Code

```bash
git clone git@github.com:dom-robinson/stats.git
cd stats
```

## Step 2: Configure

Copy the environment template and edit it:

```bash
cp ENV_TEMPLATE .env
```

Edit `.env` with your credentials:

```bash
# TP-Link API Credentials
TPLINK_CLIENT_ID=your-client-id-here
TPLINK_CLIENT_SECRET=your-secret-here
TPLINK_REFRESH_TOKEN=your-refresh-token-here

# PostgreSQL/TimescaleDB Setup (will auto-create if needed)
POSTGRES_DB=gos_rem
POSTGRES_USER=gos
POSTGRES_PASSWORD=your-secure-password-here

# Grafana Setup
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your-secure-password-here

# Ports (optional - defaults shown)
ADMIN_PORT=7001
INFLUXDB_PORT=7002
GRAFANA_PORT=7003

# Collector Settings
POLL_INTERVAL=30
```

**Important**: Keep your `.env` file secret! It contains sensitive credentials.

## Step 3: Start Everything

```bash
docker-compose up -d
```

This will:
- Download all required images
- Start the data collector
- Start TimescaleDB database (PostgreSQL with time-series extension)
- Start Grafana dashboard (optional)
- Start the Admin UI / Data Exploration Tool

Wait about 30 seconds for everything to start, then check status:

```bash
docker-compose ps
```

All services should show "Up" status.

## Step 4: Access the System

- **Admin UI / Data Exploration Tool**: http://localhost:7001
- **Grafana** (optional): http://localhost:7003 (admin/admin or your credentials)

## Step 5: View Data

1. Open the Admin UI: http://localhost:7001
2. Go to "Manage Groups" to create experiment groups
3. Go to "Exploration" to view charts and analyze data
4. Data will start appearing within 30 seconds of startup

## Stopping the System

```bash
docker-compose down
```

To stop but keep data:

```bash
docker-compose stop
```

## Troubleshooting

### Check Logs

```bash
# See all logs
docker-compose logs

# See collector logs (data collection)
docker-compose logs -f collector

# See admin UI logs
docker-compose logs -f admin
```

### Reset Everything (Warning: Deletes All Data!)

```bash
docker-compose down -v
docker-compose up -d
```

### Common Issues

**No data appearing?**
- Check collector logs: `docker-compose logs collector`
- Verify TP-Link credentials in `.env`
- Check if devices are online in TP-Link app

**Can't access Grafana?**
- Wait 30 seconds for full startup
- Check logs: `docker-compose logs grafana`
- Verify credentials in `.env`

**Ports already in use?**
- Change ports in `.env` (ADMIN_PORT, GRAFANA_PORT, etc.)
- Restart: `docker-compose restart`

## Next Steps

- Create experiment groups in the Admin UI
- Configure Grafana dashboards (optional)
- Set up data retention policies
- Enable automatic backups

For more details, see [README.md](README.md).

