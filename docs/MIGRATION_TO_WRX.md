# Migration Guide: Stats from Pi400 to WRX with NAS Storage

This guide walks through migrating the stats system from Pi400 to WRX, with all data stored on the NAS attached drive instead of local SD card storage.

## Prerequisites

- Access to both Pi400 and WRX machines
- NAS drive mounted on WRX (default: `/mnt/nas/stats`)
- Docker and Docker Compose installed on WRX
- Git repository cloned on WRX

## Migration Steps

### Step 1: Export Data from Pi400

#### Option A: Use Admin UI Export (Recommended)
1. Navigate to http://stats.liveencode.com/admin (or Pi400 IP:7001/admin)
2. Click **"Export Database"** button
3. Download the ZIP file containing:
   - Database dump (pg_dump format)
   - device_groups.json
   - experiments.json
   - annotations.json
   - snapshots.json
   - snapshots/ directory

#### Option B: Manual Export via SSH
```bash
# SSH to Pi400
ssh d2@pi400

# Navigate to stats directory
cd /home/d2/stats

# Export database
docker exec stats-timescaledb pg_dump -U gos -d gos_rem -Fc > /tmp/stats_backup.dump

# Copy JSON files
tar -czf /tmp/stats_data.tar.gz \
  admin/data/device_groups.json \
  admin/data/experiments.json \
  admin/data/annotations.json \
  admin/data/snapshots.json \
  admin/data/snapshots/

# Copy collector token
cp /var/lib/docker/volumes/stats_collector-data/_data/refresh_token.txt /tmp/

# Transfer files to WRX (adjust path as needed)
scp /tmp/stats_backup.dump d2@wrx:/tmp/
scp /tmp/stats_data.tar.gz d2@wrx:/tmp/
scp /tmp/refresh_token.txt d2@wrx:/tmp/
```

### Step 2: Prepare WRX

1. **Identify NAS mount point:**
   ```bash
   ssh d2@wrx
   df -h | grep -i nas
   # Or check common mount points:
   ls -la /mnt/ | grep nas
   ls -la /media/ | grep nas
   ```

2. **Create data directories on NAS:**
   ```bash
   # Set NAS path (adjust based on your actual mount point)
   export NAS_DATA_PATH=/mnt/nas/stats  # Update this!
   
   # Create directories
   sudo mkdir -p $NAS_DATA_PATH/{timescaledb,admin,collector}
   sudo chown -R $USER:$USER $NAS_DATA_PATH
   
   # Verify permissions
   ls -la $NAS_DATA_PATH
   ```

3. **Clone repository on WRX:**
   ```bash
   cd ~
   git clone <your-stats-repo-url> stats
   cd stats
   ```

4. **Create .env file:**
   ```bash
   cp ENV_TEMPLATE .env
   # Edit .env with your credentials and NAS path:
   # NAS_DATA_PATH=/mnt/nas/stats  # Add this line
   # POSTGRES_PASSWORD=your-password
   # TPLINK_CLIENT_SECRET=your-secret
   # TPLINK_REFRESH_TOKEN=your-token
   ```

### Step 3: Update docker-compose.yml on WRX

Replace `docker-compose.yml` with `docker-compose.nas.yml`:

```bash
cd ~/stats
cp docker-compose.yml docker-compose.yml.old  # Backup original
cp docker-compose.nas.yml docker-compose.yml
```

Or manually update volumes section to use bind mounts:
- Replace `timescaledb-data:/var/lib/postgresql/data` with `${NAS_DATA_PATH}/timescaledb:/var/lib/postgresql/data`
- Replace `admin-data:/app/data` with `${NAS_DATA_PATH}/admin:/app/data`
- Replace `collector-data:/app/data` with `${NAS_DATA_PATH}/collector:/app/data`
- Remove the `volumes:` section at the bottom (no named volumes needed)

### Step 4: Restore Data on WRX

1. **Start TimescaleDB first (empty):**
   ```bash
   cd ~/stats
   docker compose up -d timescaledb
   # Wait for it to be healthy
   docker compose ps
   ```

2. **Restore database:**
   ```bash
   # Copy backup to container
   docker cp /tmp/stats_backup.dump stats-timescaledb:/tmp/
   
   # Restore database
   docker exec stats-timescaledb pg_restore -U gos -d gos_rem -v /tmp/stats_backup.dump
   
   # Verify restore
   docker exec stats-timescaledb psql -U gos -d gos_rem -c "SELECT COUNT(*) FROM gos_rem;"
   ```

3. **Restore JSON files and snapshots:**
   ```bash
   # Extract to NAS admin directory
   cd $NAS_DATA_PATH/admin
   tar -xzf /tmp/stats_data.tar.gz
   
   # Verify files
   ls -la
   ls -la snapshots/ | head -10
   ```

4. **Restore collector token:**
   ```bash
   cp /tmp/refresh_token.txt $NAS_DATA_PATH/collector/
   chmod 600 $NAS_DATA_PATH/collector/refresh_token.txt
   ```

### Step 5: Start All Services

```bash
cd ~/stats
docker compose up -d

# Check status
docker compose ps

# Check logs
docker compose logs -f
```

### Step 6: Verify Everything Works

1. **Check database:**
   ```bash
   docker exec stats-timescaledb psql -U gos -d gos_rem -c \
     "SELECT COUNT(*), MAX(time) FROM gos_rem;"
   ```

2. **Check admin UI:**
   - Navigate to http://wrx-ip:7001 (or configure reverse proxy)
   - Verify experiments, groups, and snapshots are visible

3. **Check collector:**
   ```bash
   docker compose logs collector | tail -20
   # Should see "Wrote X points" messages
   ```

4. **Verify data is on NAS:**
   ```bash
   du -sh $NAS_DATA_PATH/*
   # Should see:
   # timescaledb/  - ~136MB
   # admin/        - ~1-10MB
   # collector/    - <1MB
   ```

### Step 7: Update Reverse Proxy (if needed)

If using Traefik or another reverse proxy on WRX:
1. Update DNS to point to WRX
2. Update proxy configuration if needed
3. Test https://stats.liveencode.com

### Step 8: Stop Services on Pi400

Once verified everything works on WRX:

```bash
ssh d2@pi400
cd /home/d2/stats
docker compose down

# Optional: Backup one more time before stopping
```

## Rollback Plan

If migration fails:

1. Keep Pi400 services running until WRX is fully verified
2. If rollback needed, just restart on Pi400:
   ```bash
   ssh d2@pi400
   cd /home/d2/stats
   docker compose up -d
   ```

## Post-Migration Cleanup

After successful migration:

1. **On WRX:** Verify all data is on NAS and working
2. **On Pi400:** Optionally clean up old Docker volumes:
   ```bash
   docker volume rm stats_timescaledb-data stats_admin-data stats_collector-data
   ```

## Benefits of NAS Storage

- **No SD card wear**: All writes go to NAS
- **Better backup**: NAS likely has backup/redundancy
- **More space**: NAS has much more storage than SD card
- **Performance**: NAS may have better I/O performance
- **Centralized**: All data in one place for backups

## Troubleshooting

### Permission Issues
```bash
# If containers can't write to NAS:
sudo chown -R $USER:$USER $NAS_DATA_PATH
sudo chmod -R 755 $NAS_DATA_PATH
```

### Database Restore Fails
```bash
# Drop and recreate database:
docker exec stats-timescaledb psql -U gos -d postgres -c "DROP DATABASE gos_rem;"
docker exec stats-timescaledb psql -U gos -d postgres -c "CREATE DATABASE gos_rem;"
# Then restore again
```

### Services Won't Start
```bash
# Check NAS mount:
df -h | grep nas
mount | grep nas

# Check directory permissions:
ls -la $NAS_DATA_PATH

# Check Docker logs:
docker compose logs timescaledb
docker compose logs admin
docker compose logs collector
```

---

**Last Updated**: 2025-12-23  
**Migration Date**: TBD



