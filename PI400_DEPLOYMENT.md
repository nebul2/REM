# Deploying GOS REM to Pi400 and Decommissioning Old System

## Overview

This document outlines the steps to:
1. Deploy the new Docker-based GOS REM system to Pi400
2. Decommission the old native InfluxDB/Grafana installation
3. Remove old scripts and cron jobs

## Prerequisites

- SSH access to Pi400
- Docker and Docker Compose installed on Pi400
- Backup of current data (optional but recommended)

## Step 1: Backup Current Data (Optional but Recommended)

```bash
ssh pi400

# Backup InfluxDB data
sudo systemctl stop influxdb
sudo tar -czf ~/influxdb-backup-$(date +%Y%m%d).tar.gz /var/lib/influxdb2/
sudo systemctl start influxdb

# Backup Grafana data
sudo systemctl stop grafana-server
sudo tar -czf ~/grafana-backup-$(date +%Y%m%d).tar.gz /var/lib/grafana/
sudo systemctl start grafana-server
```

## Step 2: Install Docker on Pi400

If Docker is not already installed:

```bash
ssh pi400

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (if needed)
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Log out and back in for group changes to take effect
exit
```

## Step 3: Clone Repository on Pi400

```bash
ssh pi400

# Navigate to your desired location
cd ~

# Clone the repo
git clone git@github.com:dom-robinson/stats.git
cd stats
```

## Step 4: Configure Environment

```bash
# Copy template
cp ENV_TEMPLATE .env

# Edit with your credentials (use nano or vim)
nano .env
```

**Important**: Get the existing InfluxDB token from the old system:

```bash
# On Pi400, check existing InfluxDB token
sudo cat /var/lib/influxdb2/configs 2>/dev/null | grep token || echo "Check InfluxDB setup page"
```

You may need to create a new token from the old InfluxDB UI, or start fresh.

## Step 5: Start New Docker System

```bash
cd ~/stats

# Start all services
docker-compose up -d

# Wait for startup (30 seconds)
sleep 30

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

## Step 6: Verify New System is Working

1. Check Admin UI: http://pi400:7001 (or http://stats.liveencode.com:7001 if DNS is configured)
2. Check data is being collected: `docker-compose logs collector`
3. Verify data in InfluxDB via Admin UI

## Step 7: Decommission Old System

**⚠️ WARNING: Only do this after confirming the new system works!**

### Stop Old Services

```bash
ssh pi400

# Stop old services
sudo systemctl stop grafana-server
sudo systemctl stop influxdb
sudo systemctl disable grafana-server
sudo systemctl disable influxdb
```

### Remove Old Cron Jobs

```bash
# Edit crontab
crontab -e

# Remove any lines related to:
# - cloudcollect.py
# - tplink_to_influxdb
# - energy monitoring scripts

# Or disable specific cron job by commenting it out:
# * * * * * /home/d2/tplink_to_influxdb/app/cloudcollect.py
```

### Remove Old Data Collector Script

```bash
# Backup old scripts (optional)
mkdir -p ~/backups/old-stats-system
cp -r /home/d2/tplink_to_influxdb ~/backups/old-stats-system/ 2>/dev/null || true

# Remove old scripts (when ready)
# rm -rf /home/d2/tplink_to_influxdb
```

### Remove Old Services (Optional - After Confirming Everything Works)

```bash
# Remove Grafana
sudo apt remove grafana-server -y
sudo apt autoremove -y

# Remove InfluxDB
sudo apt remove influxdb2 -y
sudo apt autoremove -y

# Clean up old data (ONLY if you're sure new system has all data)
# sudo rm -rf /var/lib/influxdb2
# sudo rm -rf /var/lib/grafana
```

## Step 8: Update DNS/Port Forwarding (If Needed)

If you were accessing via `stats.liveencode.com`:

1. Update DNS to point to port 7001 for Admin UI
2. Update port forwarding if behind router
3. Update any bookmarks/links

## Step 9: Set Up Auto-Start (Optional)

To ensure the Docker system starts on boot:

```bash
# Create systemd service (optional)
sudo nano /etc/systemd/system/gos-rem.service
```

Add:

```ini
[Unit]
Description=GOS REM Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/d2/stats
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=d2
Group=d2

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo systemctl enable gos-rem.service
sudo systemctl start gos-rem.service
```

## Step 10: Monitor and Test

1. Let the new system run for 24-48 hours
2. Compare data between old and new systems
3. Verify all features work
4. Then permanently remove old system

## Rollback Plan (If Needed)

If something goes wrong:

```bash
# Stop new system
cd ~/stats
docker-compose down

# Restore old services
sudo systemctl start influxdb
sudo systemctl start grafana-server
sudo systemctl enable influxdb
sudo systemctl enable grafana-server

# Restore cron jobs if needed
crontab -e
# Uncomment old cron job
```

## Data Migration (If Needed)

If you want to migrate old InfluxDB data to new system:

1. Export data from old InfluxDB using `influx` CLI
2. Import into new InfluxDB using `influx` CLI or admin tools
3. This is complex - may be easier to just start fresh

## Notes

- Old system data is at: `/var/lib/influxdb2/` and `/var/lib/grafana/`
- Old scripts are at: `/home/d2/tplink_to_influxdb/`
- New system data is in Docker volumes (managed by docker-compose)
- To see Docker volumes: `docker volume ls`
- To backup new system: `docker-compose down` then backup volumes

