# DevBench Integration Complete ✅

## Summary

The `stats` project has been successfully integrated into DevBench for automated deployment management. You can now deploy to pi400 staging directly from the DevBench dashboard or CLI.

## What Was Done

### 1. Updated DevBench Configuration

**File**: `.devbench/config/environments.yaml`
- ✅ Updated `pi400` environment to support Traefik
- ✅ Changed SSH user from `pi` to `d2`
- ✅ Added `traefik_enabled: true`
- ✅ Added `traefik_domain: stats.liveencode.com`

**File**: `.devbench/scripts/deploy.sh`
- ✅ Added complete `pi400` deployment handler (~230 lines)
- ✅ Automatically detects and uses `docker-compose.traefik.yml`
- ✅ Handles environment file copying from DevBench secrets
- ✅ Supports SSH config or explicit credentials
- ✅ Updates `deployed_commits` in `projects.yaml`

### 2. Created Documentation

**File**: `DEVBENCH_DEPLOYMENT_INSTRUCTIONS.md`
- Complete guide for DevBench integration
- Deployment process documentation
- Environment variable requirements

## How to Use

### Deploy via DevBench CLI

```bash
# From DevBench root directory
cd ~/Desktop/cursor-devbench
.devbench/scripts/deploy.sh stats pi400
```

Or via DevBench dashboard:
- Navigate to Stats project
- Click "Deploy" → Select "pi400" environment

### First-Time Setup

1. **Create Environment File** (one-time setup):
   ```bash
   # Create the environment file on pi400 manually OR
   # Copy from your existing .env on pi400:
   scp d2@pi400:~/stats/.env ~/Desktop/cursor-devbench/.devbench/config/secrets/stats.pi400.env
   
   # Or create it manually with your credentials
   nano ~/Desktop/cursor-devbench/.devbench/config/secrets/stats.pi400.env
   ```

2. **Ensure SSH Access**:
   ```bash
   # Test SSH connection
   ssh d2@pi400
   
   # Or add to ~/.ssh/config:
   Host pi400
     HostName pi400
     User d2
     IdentityFile ~/.ssh/id_rsa
   ```

3. **Ensure GitHub SSH Key on pi400**:
   ```bash
   ssh d2@pi400
   # Make sure GitHub SSH key is configured for git clone/pull
   ```

## Environment File Template

The environment file should be located at:
```
.devbench/config/secrets/stats.pi400.env
```

**Required Variables:**
```bash
# TP-Link API Credentials
TPLINK_CLIENT_ID=fdcae128-0adf-4233-8a58-30760652bd16
TPLINK_CLIENT_SECRET=your-secret
TPLINK_API_KEY=e71bf02f-8b71-42ee-8af0-62a7bdf6c866
TPLINK_REFRESH_TOKEN=your-refresh-token

# PostgreSQL/TimescaleDB
POSTGRES_DB=gos_rem
POSTGRES_USER=gos
POSTGRES_PASSWORD=your-secure-password

# Collector Settings
POLL_INTERVAL=30

# Grafana (optional)
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your-secure-password

# Ports
ADMIN_PORT=7001
GRAFANA_PORT=7003
```

**Note**: The `GIT_COMMIT` variable is automatically set by DevBench during deployment.

## Deployment Process

When you run `devbench deploy stats pi400`, DevBench will:

1. **SSH to pi400** as user `d2`
2. **Clone/Update Repository** from GitHub
3. **Copy Environment File** from `.devbench/config/secrets/stats.pi400.env`
4. **Deploy with Traefik** - automatically uses `docker-compose.traefik.yml`
5. **Verify Deployment** - checks container status
6. **Update Status** - records deployed commit in `projects.yaml`

## What Happens During Deployment

```
🌐 Deploying to remote server: pi400
   SSH Host: d2@pi400
   GitHub URL: git@github.com:dom-robinson/stats.git
   Remote directory: /home/d2/stats

📥 Step 1: Cloning/updating repository on pi400...
   ✅ Remote commit: abc1234

📝 Step 2: Managing environment file...
   ✅ Environment file copied

🛑 Step 3: Stopping existing containers...
   Killing: stats-timescaledb
   Killing: stats-collector
   ...

🚀 Step 4: Building and starting containers...
   ✅ Using Traefik override file (docker-compose.traefik.yml)
   ✅ Containers started

✅ Step 5: Checking container status...
   ✅ Deployment to pi400 complete!
   📍 Access at: https://stats.liveencode.com
   📍 Direct access: http://pi400:7001
```

## Verification

After deployment, verify:

```bash
# Check containers are running
ssh d2@pi400 "cd ~/stats && docker-compose ps"

# Check Traefik routing
curl -I https://stats.liveencode.com
# Should redirect to Authelia login

# Check collector is polling
ssh d2@pi400 "docker logs stats-collector | tail -10"
```

## Changes Committed

✅ **DevBench Repository**: Changes committed and pushed
- `.devbench/config/environments.yaml`
- `.devbench/scripts/deploy.sh`

✅ **Stats Repository**: Documentation added
- `DEVBENCH_DEPLOYMENT_INSTRUCTIONS.md`
- `DEVBENCH_INTEGRATION_COMPLETE.md` (this file)

## Next Steps

1. **Create Environment File**:
   - Copy your existing `.env` from pi400 to `.devbench/config/secrets/stats.pi400.env`
   - Or create it manually with the template

2. **Test Deployment**:
   ```bash
   devbench deploy stats pi400
   ```

3. **Monitor via DevBench Dashboard**:
   - View deployment status
   - See deployed commit hash
   - Access deployment logs

## Future: Akamai Linode Production

When Akamai Linode access is available:
- Similar process will work for `akamai-linode` environment
- Just need to configure environment details in `environments.yaml`
- Production deployment will follow same workflow

---

**Status**: ✅ Integration Complete - Ready for deployment via DevBench!

