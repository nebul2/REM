# Power Cut Recovery Configuration

This document describes the measures in place to ensure the GOS REM system automatically recovers after power cuts.

## Current Configuration

### Docker Restart Policies

All containers are configured with `restart: always` in `docker-compose.yml`, which means:
- Containers will automatically restart if they stop unexpectedly
- Containers will restart when Docker daemon starts (e.g., after a reboot)
- Containers will restart even if manually stopped (unless explicitly removed)

### Health Checks

All services have health checks configured:
- **TimescaleDB**: Checks database readiness every 10s
- **Collector**: Verifies Python process is running every 30s
- **Admin**: Tests HTTP endpoint every 30s
- **Grafana**: Tests HTTP health endpoint every 10s

Health checks allow Docker to detect and restart unhealthy containers.

### System-Level Auto-Start

#### Docker Service
The Docker service is enabled to start on boot:
```bash
systemctl is-enabled docker  # Should show "enabled"
```

#### Docker Compose Stack
To ensure the stack starts automatically on boot, you can:

**Option 1: Use systemd service (Recommended)**

Create a systemd service file on the Pi400:

```bash
sudo nano /etc/systemd/system/gos-stats.service
```

Add the following content:
```ini
[Unit]
Description=GOS REM Stats Docker Compose Stack
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/d2/stats
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0
User=d2
Group=d2

[Install]
WantedBy=multi-user.target
```

Then enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable gos-stats.service
sudo systemctl start gos-stats.service
```

**Option 2: Use crontab (Simple but less robust)**

Add to crontab:
```bash
crontab -e
```

Add this line:
```
@reboot cd /home/d2/stats && /usr/bin/docker compose up -d
```

## Verification

After a power cut or reboot, verify the system is running:

```bash
# Check Docker is running
systemctl status docker

# Check all containers are up
cd /home/d2/stats
docker compose ps

# Check container logs if needed
docker compose logs --tail=50
```

## Troubleshooting

### Containers Not Starting After Reboot

1. **Check Docker service**:
   ```bash
   systemctl status docker
   ```

2. **Check if systemd service exists** (if using Option 1):
   ```bash
   systemctl status gos-stats.service
   ```

3. **Manually start the stack**:
   ```bash
   cd /home/d2/stats
   docker compose up -d
   ```

4. **Check container logs**:
   ```bash
   docker compose logs timescaledb
   docker compose logs collector
   docker compose logs admin
   ```

### Containers Showing as "Unhealthy"

1. **Wait for health checks**: Containers may show as "unhealthy" during startup. Wait 30-60 seconds.

2. **Check health check logs**:
   ```bash
   docker inspect stats-admin | grep -A 10 Health
   ```

3. **Restart specific container**:
   ```bash
   docker compose restart admin
   ```

4. **Check dependencies**: Ensure TimescaleDB is healthy before other services start.

### Database Connection Issues After Reboot

If the database takes longer to start:
- TimescaleDB has a 30-second `start_period` for health checks
- Other services wait for TimescaleDB to be healthy before starting
- If issues persist, increase `start_period` in docker-compose.yml

## Manual Recovery Steps

If automatic recovery fails:

1. **SSH to Pi400**:
   ```bash
   ssh d2@pi400
   ```

2. **Navigate to project directory**:
   ```bash
   cd /home/d2/stats
   ```

3. **Stop all containers**:
   ```bash
   docker compose down
   ```

4. **Start all containers**:
   ```bash
   docker compose up -d
   ```

5. **Monitor startup**:
   ```bash
   docker compose ps
   docker compose logs -f
   ```

6. **Wait for all containers to be healthy** (may take 1-2 minutes)

## Best Practices

1. **Regular Backups**: Ensure database backups are configured (see `docs/DATA_RETENTION.md`)

2. **Monitor Logs**: Set up log monitoring to detect issues early

3. **UPS**: Consider using an Uninterruptible Power Supply (UPS) for the Pi400 to handle brief power interruptions

4. **Test Recovery**: Periodically test recovery by rebooting the Pi400:
   ```bash
   sudo reboot
   ```

## Current Status

✅ **Docker service**: Enabled to start on boot  
✅ **Container restart policy**: `restart: always` for all services  
✅ **Health checks**: Configured for all services  
⚠️ **Docker Compose auto-start**: Requires systemd service or crontab (see above)

---

**Last Updated**: 2025-12-08  
**Version**: 1.1.0

