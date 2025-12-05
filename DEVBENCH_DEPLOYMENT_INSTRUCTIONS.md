# DevBench Deployment Instructions for stats.liveencode.com

## Overview

This document provides instructions for integrating the `stats` project deployment into DevBench so it can be managed through the DevBench dashboard and deployment system.

## Current Status

The `stats` project is already partially configured in DevBench:
- ✅ Project defined in `.devbench/config/projects.yaml`
- ✅ Deployment target `pi400` exists in `.devbench/config/deployment-targets.yaml`
- ✅ Basic `pi400` environment exists in `.devbench/config/environments.yaml`
- ⚠️  **Missing**: Traefik configuration and deployment handler for `pi400` environment

## Required Changes

I've created **two options** - choose the one that best fits your workflow:

### Option 1: Update Existing pi400 Environment (Recommended)

Update the existing `pi400` environment to support Traefik for stats deployments.

**File**: `.devbench/config/environments.yaml`

Update the `pi400` section (around line 74):

```yaml
  pi400:
    name: pi400 (Raspberry Pi 400)
    description: Raspberry Pi 400 for staging deployments (GOS projects)
    docker_host: pi400
    default_ports_start: 3000
    ssh_user: d2  # Changed from 'pi' to match your setup
    ssh_key: ~/.ssh/id_rsa
    requires_approval: false
    type: docker
    traefik_enabled: true  # ADD THIS
    traefik_domain: stats.liveencode.com  # ADD THIS (for stats project)
    notes: Staging environment for GOS projects. Stats project uses Traefik reverse proxy at stats.liveencode.com. Accessible via https://stats.liveencode.com with Authelia authentication.
```

**Benefits:**
- Simple - just update existing config
- Works for all GOS projects on pi400
- Can add more Traefik domains later for other projects

### Option 2: Create Separate pi400-staging Environment

Keep the existing `pi400` for non-Traefik deployments and create a new environment for staging.

**File**: `.devbench/config/environments.yaml`

Add this new environment entry after `pi400`:

```yaml
  pi400-staging:
    name: pi400 Staging (Traefik)
    description: Raspberry Pi 400 staging environment with Traefik reverse proxy for stats.liveencode.com
    docker_host: pi400
    default_ports_start: 3000
    ssh_user: d2
    ssh_key: ~/.ssh/id_rsa
    requires_approval: false
    type: docker
    traefik_enabled: true
    traefik_domain: stats.liveencode.com
    notes: Staging environment for stats.liveencode.com. Behind Traefik reverse proxy with Authelia authentication. Uses docker-compose.traefik.yml override file.
```

Then update **File**: `.devbench/config/deployment-targets.yaml`

Change stats deployment targets to:

```yaml
  stats:
    - local
    - pi400-staging  # New staging environment
    - pi400          # Keep for non-Traefik deployments if needed
    - akamai-linode
```

**Benefits:**
- Clear separation between staging and development
- Can have different configurations per environment

## Deployment Handler

The DevBench `deploy.sh` script needs to handle `pi400` deployments. Currently, there's no handler for `pi400` in the switch statement.

**File**: `.devbench/scripts/deploy.sh`

Add a new case handler (similar to `wrx` or `ttns-dev`) around line 740, before the `*)` default case:

```bash
  pi400)
    # Remote deployment to pi400 (Raspberry Pi 400 with Traefik)
    echo "🌐 Deploying to remote server: pi400"
    
    # Load environment config
    ENV_CONFIG_FILE="$DEVBENCH_ROOT/config/environments.yaml"
    SSH_HOST=$(grep -A 10 "^  pi400:" "$ENV_CONFIG_FILE" | grep "docker_host:" | sed 's/.*docker_host:[[:space:]]*"\(.*\)"/\1/' | tr -d '"')
    SSH_USER=$(grep -A 10 "^  pi400:" "$ENV_CONFIG_FILE" | grep "ssh_user:" | sed 's/.*ssh_user:[[:space:]]*\(.*\)/\1/' | sed 's/null//' | tr -d '"' | tr -d ' ')
    SSH_KEY=$(grep -A 10 "^  pi400:" "$ENV_CONFIG_FILE" | grep "ssh_key:" | sed 's/.*ssh_key:[[:space:]]*"\(.*\)"/\1/' | sed 's|~|'"$HOME"'|' | tr -d '"')
    
    if [ -z "$SSH_HOST" ]; then
      echo "❌ Could not determine SSH host from environments.yaml"
      exit 1
    fi
    
    # Default SSH user if not set
    if [ -z "$SSH_USER" ] || [ "$SSH_USER" = "null" ]; then
      SSH_USER="d2"
    fi
    
    # Default SSH key if not set
    if [ -z "$SSH_KEY" ] || [ "$SSH_KEY" = "null" ]; then
      SSH_KEY="$HOME/.ssh/id_rsa"
    fi
    
    # Expand ~ in SSH key path
    SSH_KEY=$(echo "$SSH_KEY" | sed "s|^~|$HOME|")
    
    echo "   SSH Host: $SSH_USER@$SSH_HOST"
    echo "   SSH Key: $SSH_KEY"
    
    # Check if project has GitHub URL
    GITHUB_URL=$(grep -A 20 "id: $PROJECT_ID" "$DEVBENCH_ROOT/config/projects.yaml" | grep "github:" | head -1 | sed 's/.*github:[[:space:]]*\(.*\)/\1/' | tr -d '"')
    
    if [ -z "$GITHUB_URL" ] || [ "$GITHUB_URL" = "null" ]; then
      echo "❌ Project does not have a GitHub URL configured"
      echo "   Remote deployment requires a GitHub repository"
      exit 1
    fi
    
    # Ensure we use SSH format for GitHub URLs (remote server has SSH key)
    if echo "$GITHUB_URL" | grep -q "^https://github.com/"; then
      GITHUB_URL=$(echo "$GITHUB_URL" | sed 's|https://github.com/|git@github.com:|' | sed 's|\.git$||')".git"
    fi
    
    echo "   GitHub URL: $GITHUB_URL"
    echo "   Note: Remote server needs GitHub SSH key configured"
    
    # Determine remote project directory
    PROJECT_NAME=$(basename "$PROJECT_PATH")
    REMOTE_PROJECT_DIR="/home/$SSH_USER/$PROJECT_NAME"
    
    echo "   Remote directory: $REMOTE_PROJECT_DIR"
    echo ""
    
    # Build SSH command prefix (use SSH config if available, otherwise explicit)
    if grep -q "Host.*pi400" ~/.ssh/config 2>/dev/null; then
      SSH_CMD="ssh -o StrictHostKeyChecking=no pi400"
      SCP_CMD="scp -o StrictHostKeyChecking=no"
      RSYNC_CMD="rsync -e 'ssh -o StrictHostKeyChecking=no'"
    else
      SSH_CMD="ssh -i $SSH_KEY -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST"
      SCP_CMD="scp -i $SSH_KEY -o StrictHostKeyChecking=no"
      RSYNC_CMD="rsync -e 'ssh -i $SSH_KEY -o StrictHostKeyChecking=no'"
    fi
    
    # Step 1: Clone/Update repository
    echo "📥 Step 1: Cloning/updating repository on pi400..."
    
    $SSH_CMD "mkdir -p ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts 2>&1 || true" || true
    
    $SSH_CMD "if [ -d \"$REMOTE_PROJECT_DIR/.git\" ]; then
      echo '   Repository exists, pulling latest from master...'
      cd \"$REMOTE_PROJECT_DIR\" && \
        git fetch origin 2>&1 && \
        git reset --hard origin/master 2>&1
    elif [ -d \"$REMOTE_PROJECT_DIR\" ]; then
      echo '   Directory exists but is not a git repo, removing and cloning fresh...'
      rm -rf \"$REMOTE_PROJECT_DIR\"
      mkdir -p \"$(dirname $REMOTE_PROJECT_DIR)\"
      cd \"$(dirname $REMOTE_PROJECT_DIR)\" && git clone \"$GITHUB_URL\" \"$PROJECT_NAME\"
    else
      echo '   Repository does not exist, cloning...'
      mkdir -p \"$(dirname $REMOTE_PROJECT_DIR)\"
      cd \"$(dirname $REMOTE_PROJECT_DIR)\" && git clone \"$GITHUB_URL\" \"$PROJECT_NAME\"
    fi" || {
      echo "❌ Failed to clone/pull repository"
      exit 1
    }
    
    REMOTE_COMMIT=$($SSH_CMD "cd \"$REMOTE_PROJECT_DIR\" && git rev-parse --short HEAD 2>/dev/null" || echo "")
    
    if [ -n "$REMOTE_COMMIT" ]; then
      echo "   ✅ Remote commit: $REMOTE_COMMIT"
      GIT_COMMIT="$REMOTE_COMMIT"
    else
      GIT_COMMIT=$(cd "$PROJECT_DIR" && git rev-parse --short HEAD 2>/dev/null || echo "")
    fi
    
    # Step 2: Copy/Update .env file (if exists locally)
    echo ""
    echo "📝 Step 2: Managing environment file..."
    
    # Check if environment-specific env file exists in DevBench config
    ENV_FILE="$DEVBENCH_ROOT/config/secrets/${PROJECT_ID}.${ENV}.env"
    if [ -f "$ENV_FILE" ]; then
      echo "   Copying environment file from DevBench config..."
      $SCP_CMD "$ENV_FILE" "$SSH_USER@$SSH_HOST:$REMOTE_PROJECT_DIR/.env" || {
        echo "⚠️  Warning: Could not copy environment file via scp"
      }
    elif [ -f "$PROJECT_DIR/.env" ]; then
      echo "   Copying .env file from project directory..."
      $SCP_CMD "$PROJECT_DIR/.env" "$SSH_USER@$SSH_HOST:$REMOTE_PROJECT_DIR/.env" || {
        echo "⚠️  Warning: Could not copy .env file via scp"
      }
    else
      echo "   ⚠️  No .env file found - containers will use default environment variables"
    fi
    
    # Update GIT_COMMIT in remote .env file if it exists
    if [ -n "$GIT_COMMIT" ]; then
      $SSH_CMD "cd \"$REMOTE_PROJECT_DIR\" && \
        if [ -f .env ]; then
          if grep -q '^GIT_COMMIT=' .env 2>/dev/null; then
            sed -i 's/^GIT_COMMIT=.*/GIT_COMMIT=$GIT_COMMIT/' .env
          else
            echo 'GIT_COMMIT=$GIT_COMMIT' >> .env
          fi
        fi" || {
        echo "   ⚠️  Failed to update GIT_COMMIT in remote .env file"
      }
    fi
    
    # Step 3: Stop and remove existing containers
    echo ""
    echo "🛑 Step 3: Stopping existing containers..."
    
    $SSH_CMD "cd \"$REMOTE_PROJECT_DIR\" && \
      if [ -f docker-compose.yml ]; then
        # Extract container names from compose file
        container_names=\$(grep -E 'container_name:' docker-compose.yml | sed 's/.*container_name:[[:space:]]*//' | sed 's/[[:space:]]*$//' | tr '\n' ' ')
        
        # Kill all running containers immediately
        for container_name in \$container_names; do
          if [ -n \"\$container_name\" ]; then
            if docker ps --filter \"name=^\${container_name}\$\" --format '{{.Names}}' 2>/dev/null | grep -q \"^\${container_name}\$\"; then
              echo \"   Killing: \$container_name\"
              docker kill \"\${container_name}\" 2>&1 || true
            fi
          fi
        done
        
        # Remove containers
        for container_name in \$container_names; do
          if [ -n \"\$container_name\" ]; then
            docker rm -f \"\${container_name}\" 2>&1 || true
          fi
        done
        
        # Clean up with compose
        timeout 2 docker compose down --timeout 1 --remove-orphans 2>&1 || timeout 2 docker-compose down --timeout 1 --remove-orphans 2>&1 || true
      fi" || true
    
    # Step 4: Build and start containers (with Traefik override if enabled)
    echo ""
    echo "🚀 Step 4: Building and starting containers..."
    
    $SSH_CMD "cd \"$REMOTE_PROJECT_DIR\" && \
      if [ -f docker-compose.yml ]; then
        # Check for Traefik override file (docker-compose.traefik.yml)
        COMPOSE_FILES='-f docker-compose.yml'
        if [ -f docker-compose.traefik.yml ]; then
          COMPOSE_FILES=\"\$COMPOSE_FILES -f docker-compose.traefik.yml\"
          echo '   Using Traefik override file (docker-compose.traefik.yml)'
        fi
        
        if [ -f .env ]; then
          echo '   Using environment file: .env'
          docker-compose \$COMPOSE_FILES --env-file .env up -d --build --force-recreate 2>&1 || docker compose \$COMPOSE_FILES --env-file .env up -d --build --force-recreate 2>&1
        else
          echo '   ⚠️  WARNING: .env file not found, containers may not have all required variables'
          docker-compose \$COMPOSE_FILES up -d --build --force-recreate 2>&1 || docker compose \$COMPOSE_FILES up -d --build --force-recreate 2>&1
        fi
      else
        echo '❌ docker-compose.yml not found'
        exit 1
      fi" || {
      echo "❌ Deployment failed!"
      exit 1
    }
    
    # Step 5: Check container status
    echo ""
    echo "✅ Step 5: Checking container status..."
    $SSH_CMD "cd \"$REMOTE_PROJECT_DIR\" && \
      docker-compose ps 2>&1 || docker compose ps 2>&1 || docker ps --filter \"name=$PROJECT_NAME\""
    
    echo ""
    echo "✅ Deployment to pi400 complete!"
    echo "   📍 Access at: https://stats.liveencode.com (if Traefik configured)"
    echo "   📍 Direct access: http://pi400:7001"
    
    # Update deployed_commits in projects.yaml
    if [ -n "$GIT_COMMIT" ]; then
      update_deployed_commit "$PROJECT_ID" "pi400" "$GIT_COMMIT" || {
        echo "⚠️  Failed to update deployed_commits in projects.yaml (non-critical)"
      }
    elif [ -d "$PROJECT_DIR/.git" ]; then
      (cd "$PROJECT_DIR" && update_deployed_commit "$PROJECT_ID" "pi400") || {
        echo "⚠️  Failed to update deployed_commits in projects.yaml (non-critical)"
      }
    fi
    ;;
```

**Note**: This handler checks for `docker-compose.traefik.yml` and uses it automatically if it exists. For the stats project, this means Traefik configuration will be applied automatically.

## Environment Variables

The `.env` file on pi400 must contain:

```bash
# TP-Link API Credentials
TPLINK_CLIENT_ID=fdcae128-0adf-4233-8a58-30760652bd16
TPLINK_CLIENT_SECRET=your-secret
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

You can store this in DevBench's secrets directory:
- `.devbench/config/secrets/stats.pi400.env`

This will be automatically copied during deployment.

## Deployment Process

Once configured, you can deploy from DevBench:

```bash
# From DevBench dashboard or CLI
devbench deploy stats pi400
```

Or from the project directory:
```bash
cd ~/Desktop/cursor-devbench/gos/stats
../../.devbench/scripts/deploy.sh stats pi400
```

## Verification Steps

After deployment, verify:

1. **Containers Running**
   ```bash
   ssh d2@pi400 "cd ~/stats && docker-compose ps"
   ```

2. **Traefik Route Active**
   ```bash
   curl -I https://stats.liveencode.com
   # Should redirect to Authelia login
   ```

3. **Collector Polling**
   ```bash
   ssh d2@pi400 "docker logs stats-collector | tail -10"
   # Should show "Wrote X points to TimescaleDB"
   ```

## Current Manual Process vs DevBench

**Current Manual Process:**
```bash
# On local machine
cd ~/Desktop/cursor-devbench/gos/stats
git push origin master

# On pi400
ssh d2@pi400
cd ~/stats
git pull
docker-compose -f docker-compose.yml -f docker-compose.traefik.yml up -d --build
```

**After DevBench Integration:**
```bash
# From DevBench dashboard
# Click "Deploy" button for stats project → pi400 environment
# Or from CLI:
devbench deploy stats pi400
```

## Next Steps

1. **Choose Option 1 or Option 2** above
2. **Update environments.yaml** with chosen configuration
3. **Add pi400 handler** to deploy.sh (or I can do this automatically)
4. **Create environment file** in `.devbench/config/secrets/stats.pi400.env`
5. **Test deployment** via DevBench
6. **Update DevBench dashboard** if needed to show pi400 as deployment target

## Future: Akamai Linode Production

When Akamai Linode access is available:
- Update `akamai-linode` environment with actual host details
- Configure production deployment process
- Similar Traefik setup (or their managed solution)
- Domain: `stats.greeningofstreaming.org` (or similar)

---

**Summary**: The stats project is already mostly integrated. You just need to:
1. Update the `pi400` environment config to add Traefik support
2. Add a `pi400` case handler to `deploy.sh`
3. Create environment file in DevBench secrets directory

Would you like me to make these changes automatically, or do you prefer to review the instructions first?
