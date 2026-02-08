# Deployment Guide - GOS Stats

## Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose installed
- TP-Link refresh token
- (Optional) Existing InfluxDB token

### Steps

1. **Clone and navigate to project**
   ```bash
   cd /path/to/cursor-devbench/gos/stats
   ```

2. **Create environment file**
   ```bash
   cp ENV_TEMPLATE .env
   # Edit .env with your actual values
   ```

3. **Get TP-Link refresh token**
   - If you have it from pi400, copy it to `TPLINK_REFRESH_TOKEN` in `.env`
   - If not, you'll need to get it via OAuth (see below)

4. **Start the stack**
   ```bash
   docker-compose up -d
   ```

5. **Check logs**
   ```bash
   docker-compose logs -f collector
   ```

6. **Access services**
   - Grafana: http://localhost:7003
   - InfluxDB: http://localhost:7002

### Getting TP-Link Refresh Token (First Time)

If you don't have a refresh token:

1. **Get authorization code** (one-time):
   - Open in browser:
   ```
   https://aps1-openapi.tplinknbu.com/v1/oauth/authorize?client_id=fdcae128-0adf-4233-8a58-30760652bd16&response_type=code&scope=all&state=123456789012345678901234&redirect_uri=https://www.greeningofstreaming.org
   ```
   - Authorize and copy the `code` from redirect URL

2. **Exchange for tokens**:
   ```bash
   curl -X POST https://aps1-openapi.tplinknbu.com/v1/oauth/token \
     -d "client_id=fdcae128-0adf-4233-8a58-30760652bd16" \
     -d "client_secret=4087d4b9-5e0c-4e50-b06c-22580fc618d5" \
     -d "grant_type=code" \
     -d "code=YOUR_CODE_HERE"
   ```

3. **Save refresh token** to `.env` as `TPLINK_REFRESH_TOKEN`

### Redo TP-Link auth (stats loads but no devices list)

If the admin UI loads but devices don’t appear, the refresh token is missing or expired. Get a new one and point the collector at it:

1. **From your Mac**, run the helper script (no browser automation; it prints the authorize URL):
   ```bash
   cd /path/to/cursor-devbench/gos/stats
   chmod +x scripts/tplink-auth-refresh.sh
   ./scripts/tplink-auth-refresh.sh
   ```
2. Open the URL it prints in your browser → sign in to TP-Link/Kasa → after redirect, copy the `code` from the URL.
3. Paste the code when the script prompts. It will exchange the code for tokens and print the **refresh token**.
4. **On pi400**: set the new token and **recreate** the collector (restart does not reload `.env`):
   ```bash
   ssh pi400
   nano /home/d2/stats/.env   # set TPLINK_REFRESH_TOKEN=<the new token>
   cd /home/d2/stats && sudo docker compose up -d collector
   ```
   Use `up -d`, not `restart`, so the container gets the updated environment.
5. Reload the stats admin UI. Devices appear only after the collector has written at least one poll to the DB (wait one poll interval, e.g. 30s).

**If still no devices:**  
- You must **recreate** the collector after editing `.env`: `docker compose up -d collector` (not `restart`).  
- Check logs: `sudo docker compose logs -f collector`. You should see e.g. `TP-Link devices: N from API, M used`. If N is 0, the token is wrong or the account has no devices; if N > 0 but M is 0, all devices were skipped (offline or unsupported model – only P110, P110M, P115, HS110, KP115, EP10 are collected).  
- If logs show `relation "gos_rem" does not exist`, the TimescaleDB table was never created (e.g. init script failed). Create it manually or run the SQL in `scripts/init-timescaledb.sql` against the `gos_rem` database, then restart the collector.  
- Ensure plugs are online in the Kasa app and are one of the supported models above.

Alternatively you can do steps 1–2 manually (authorize URL + copy code), then run the collector once interactively so it can save the token into its volume:
   ```bash
   ssh pi400 'cd /home/d2/stats && sudo docker compose run --rm -it collector'
   # When it asks "Paste Code:", paste the code from the redirect URL, then Ctrl+C
   sudo docker compose up -d collector
   ```

---

## Staging Deployment (Pi400)

### Prerequisites
- SSH access to pi400
- Docker & Docker Compose installed on pi400
- Existing InfluxDB data backup (if migrating)

### Pre-Deployment Checklist

1. **Backup existing data**
   ```bash
   ssh pi400
   influx backup /tmp/influx-backup \
     -t gwTu1qAtPgIRU8eWNpLXuz92pKo6_lgV7Y4mhdMM7n_XOe-fTXts7T54P_FQJ69UMVuTyhr77Ly7XCGz9QUNAA==
   ```

2. **Extract refresh token**
   ```bash
   ssh pi400
   cat /home/d2/tplink_to_influxdb/app/refreshTokenfile.txt
   # Copy this value
   ```

3. **Check Docker installation**
   ```bash
   ssh pi400
   docker --version
   docker-compose --version
   # If not installed, install Docker
   ```

### Deployment Steps

1. **Stop native services** (temporarily)
   ```bash
   ssh pi400
   sudo systemctl stop influxdb grafana-server
   # Comment out cron job
   crontab -e  # Comment the cloudcollect.py line
   ```

2. **Copy project to pi400**
   ```bash
   # From local machine
   rsync -avz --exclude='.git' \
     ./ pi400:/home/d2/stats/
   ```

3. **Create .env file on pi400**
   ```bash
   ssh pi400
   cd /home/d2/stats
   cp ENV_TEMPLATE .env
   nano .env  # Edit with values
   ```

4. **Update ports for staging**
   Edit `docker-compose.yml` on pi400:
   ```yaml
   ports:
     - "7002:8086"  # InfluxDB (avoid conflict with native)
     - "7003:3000"  # Grafana (avoid conflict with native)
   ```

5. **Start Docker stack**
   ```bash
   cd /home/d2/stats
   docker-compose up -d
   ```

6. **Verify it's working**
   ```bash
   docker-compose logs -f collector
   # Should see data collection messages
   ```

7. **Test Grafana**
   - Access: http://pi400:7003 (or via stats.liveencode.com if DNS configured)
   - Login with admin / password from .env

### Migrate Existing Data

If you want to import old InfluxDB data:

1. **Copy backup to container**
   ```bash
   ssh pi400
   docker cp /tmp/influx-backup stats-influxdb:/backup/
   ```

2. **Restore data**
   ```bash
   docker exec stats-influxdb influx restore /backup \
     --token YOUR_INFLUXDB_TOKEN \
     --org GOS \
     --bucket rem
   ```

### Switch to Production Ports

Once everything is verified:

1. **Stop Docker stack**
   ```bash
   cd /home/d2/stats
   docker-compose down
   ```

2. **Stop and disable native services permanently**
   ```bash
   sudo systemctl stop influxdb grafana-server
   sudo systemctl disable influxdb grafana-server
   ```

3. **Update docker-compose.yml ports**
   ```yaml
   ports:
     - "8086:8086"  # InfluxDB (standard port)
     - "3000:3000"  # Grafana (standard port)
   ```

4. **Restart Docker stack**
   ```bash
   docker-compose up -d
   ```

5. **Update DNS/Reverse Proxy** (if needed)
   - If stats.liveencode.com uses nginx/traefik, update config
   - Point to port 3000 for Grafana

### Cleanup Native Installation

After 48 hours of successful operation:

1. **Remove old scripts**
   ```bash
   ssh pi400
   rm -rf /home/d2/tplink_to_influxdb
   ```

2. **Kill zombie processes**
   ```bash
   pkill -f cloudcollect.py
   ```

3. **Remove cron entries**
   ```bash
   crontab -e  # Remove/comment all tplink entries
   ```

4. **Remove native InfluxDB/Grafana** (optional, keep for backup)
   ```bash
   # Keep for 30 days as backup, then:
   sudo systemctl stop influxdb grafana-server
   sudo apt remove influxdb grafana-server
   ```

---

## Production Deployment (Linode - Future)

### Architecture Options

**Option A: Single Docker Container on Compute Instance**
- Simple setup
- Full control
- ~$5-10/month
- Manual scaling

**Option B: Serverless + Managed DB**
- Cloud Run (or equivalent) for collector
- Managed InfluxDB or Firebase
- Pay per use
- Auto-scaling

**Decision**: Will be made after staging is stable.

### General Steps (To Be Refined)

1. Create Linode account
2. Choose deployment method
3. Set up instance/container
4. Deploy Docker stack
5. Configure DNS (if needed)
6. Set up SSL/TLS
7. Configure backups
8. Monitor costs

---

## Troubleshooting

### Collector Not Starting

**Check logs:**
```bash
docker-compose logs collector
```

**Common issues:**
- Missing `TPLINK_REFRESH_TOKEN` → Set in .env
- Invalid token → Get new refresh token
- Can't connect to InfluxDB → Check network, URLs

### No Data in Grafana

**Check InfluxDB:**
```bash
docker exec stats-influxdb influx query \
  'from(bucket:"rem") |> range(start:-1h) |> count()'
```

**Check collector logs:**
```bash
docker-compose logs collector | grep "Collected"
```

### Token Refresh Failed

**Symptoms:**
- Logs show "Failed to refresh token"
- No new data after 1 hour

**Solution:**
1. Check if refresh token is still valid
2. Get new authorization code if needed
3. Update `TPLINK_REFRESH_TOKEN` in .env
4. Restart collector: `docker-compose restart collector`

### Port Conflicts

**If ports already in use:**
```bash
# Check what's using ports
sudo lsof -i :7002
sudo lsof -i :7003

# Change ports in docker-compose.yml
# Update .env with new ports
```

---

## Maintenance

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f collector
docker-compose logs -f influxdb
docker-compose logs -f grafana
```

### Restart Services
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart collector
```

### Stop/Start
```bash
# Stop all
docker-compose down

# Start all
docker-compose up -d
```

### Backup Data
```bash
# Backup InfluxDB
docker exec stats-influxdb influx backup /backup \
  --token $INFLUXDB_TOKEN \
  --org GOS \
  --bucket rem

# Copy backup out
docker cp stats-influxdb:/backup ./backup-$(date +%Y%m%d)
```

### Update Code
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build
```

---

## Environment Variables Reference

See `ENV_TEMPLATE` for all available variables.

### Required
- `TPLINK_REFRESH_TOKEN` - TP-Link OAuth refresh token
- `INFLUXDB_TOKEN` - InfluxDB admin token (auto-generated if not set)

### Optional (have defaults)
- `POLL_INTERVAL` - Polling frequency in seconds (default: 30)
- `LOG_LEVEL` - Logging level (default: INFO)
- `INFLUXDB_ORG` - InfluxDB organization (default: GOS)
- `INFLUXDB_BUCKET` - InfluxDB bucket (default: rem)

---

**Last Updated**: 2025-12-02  
**Status**: Ready for local testing

