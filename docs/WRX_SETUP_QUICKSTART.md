# Quick Start: Setup Stats on WRX with NAS Storage

This guide assumes you've already exported the database from Pi400.

## Prerequisites

- NAS directory created: `/home/pi/nas/gos_stats`
- Database backup exported from Pi400
- Git repository cloned on WRX

## Quick Setup (Automated)

```bash
# 1. Clone repo (if not already done)
cd ~
git clone <your-repo-url> stats
cd stats

# 2. Run setup script
./scripts/setup_wrx.sh

# 3. Copy database backup from Pi400 to WRX
# On your local machine or Pi400:
scp /tmp/stats_migration_*.tar.gz d2@wrx:/tmp/

# 4. Restore data
cd ~/stats
export NAS_DATA_PATH=/home/pi/nas/gos_stats
./scripts/restore_on_wrx.sh /tmp/stats_migration_*.tar.gz

# 5. Start services
docker compose up -d

# 6. Verify
docker compose ps
curl http://localhost:7001/api/devices
```

## Manual Setup (If Scripts Don't Work)

### Step 1: Create .env file

```bash
cd ~/stats
cp ENV_TEMPLATE .env
```

Edit `.env` and ensure these are set:
```bash
NAS_DATA_PATH=/home/pi/nas/gos_stats
POSTGRES_PASSWORD=your-password-here
TPLINK_CLIENT_SECRET=your-secret
TPLINK_REFRESH_TOKEN=your-token
```

### Step 2: Update docker-compose.yml

```bash
cp docker-compose.yml docker-compose.yml.old
cp docker-compose.nas.yml docker-compose.yml
```

Or manually update the volumes section in `docker-compose.yml`:
- Replace `timescaledb-data:/var/lib/postgresql/data` with `${NAS_DATA_PATH}/timescaledb:/var/lib/postgresql/data`
- Replace `admin-data:/app/data` with `${NAS_DATA_PATH}/admin:/app/data`
- Replace `collector-data:/app/data` with `${NAS_DATA_PATH}/collector:/app/data`
- Remove the `volumes:` section at the bottom

### Step 3: Create NAS directories

```bash
export NAS_DATA_PATH=/home/pi/nas/gos_stats
mkdir -p $NAS_DATA_PATH/{timescaledb,admin,collector}
```

### Step 4: Restore database backup

```bash
# Start TimescaleDB (empty)
cd ~/stats
docker compose up -d timescaledb

# Wait for it to be healthy
docker compose ps

# Copy backup to container and restore
docker cp /tmp/stats_migration_*.tar.gz stats-timescaledb:/tmp/
# Extract if it's a tar.gz, or copy database.dump directly

# Restore database
docker exec stats-timescaledb pg_restore -U gos -d gos_rem -v /tmp/database.dump
```

### Step 5: Restore admin data

```bash
# Extract admin data to NAS
cd $NAS_DATA_PATH/admin
tar -xzf /tmp/stats_migration_*/admin_data.tar.gz
```

### Step 6: Restore collector token

```bash
cp /tmp/stats_migration_*/refresh_token.txt $NAS_DATA_PATH/collector/
chmod 600 $NAS_DATA_PATH/collector/refresh_token.txt
```

### Step 7: Start all services

```bash
cd ~/stats
docker compose up -d
docker compose ps
```

## Verify Everything Works

1. **Check database:**
   ```bash
   docker exec stats-timescaledb psql -U gos -d gos_rem -c "SELECT COUNT(*), MAX(time) FROM gos_rem;"
   ```

2. **Check admin UI:**
   ```bash
   curl http://localhost:7001/api/devices
   ```

3. **Check collector:**
   ```bash
   docker compose logs collector | tail -20
   ```

4. **Verify data on NAS:**
   ```bash
   du -sh /home/pi/nas/gos_stats/*
   ```

## Troubleshooting

### Permission Errors
```bash
sudo chown -R $USER:$USER /home/pi/nas/gos_stats
chmod -R 755 /home/pi/nas/gos_stats
```

### Database Restore Fails
```bash
# Drop and recreate database
docker exec stats-timescaledb psql -U gos -d postgres -c "DROP DATABASE IF EXISTS gos_rem;"
docker exec stats-timescaledb psql -U gos -d postgres -c "CREATE DATABASE gos_rem;"
# Then restore again
```

### Services Won't Start
```bash
# Check logs
docker compose logs timescaledb
docker compose logs admin
docker compose logs collector

# Check NAS mount
ls -la /home/pi/nas/gos_stats
```

---

**NAS Path**: `/home/pi/nas/gos_stats`  
**Last Updated**: 2025-12-23



