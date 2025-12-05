# Traefik Configuration Guide

This system can work in two modes:

## Mode 1: Standalone (Default)

Works out of the box with just Docker Compose:

```bash
docker-compose up -d
```

Services accessible directly via HTTP on Docker host ports:
- `http://localhost:7001` - Admin UI
- `http://localhost:7003` - Grafana

## Mode 2: Behind Traefik Reverse Proxy

For production deployments behind Traefik (like your staging environment):

### Option A: Use Override File (Recommended)

Create or use the provided override file:

```bash
docker-compose -f docker-compose.yml -f docker-compose.traefik.yml up -d
```

This keeps the base `docker-compose.yml` clean and standalone, while the override adds Traefik configuration.

### Option B: Uncomment Labels in docker-compose.yml

If you prefer, you can uncomment the Traefik labels directly in `docker-compose.yml`:

1. Uncomment the `traefik-network` in networks section
2. Uncomment the labels section in the `admin` service
3. Ensure `traefik-network` exists: `docker network create traefik-network` (if external)

### Required Traefik Setup

1. **Create external network** (if not already exists):
   ```bash
   docker network create traefik-network
   ```

2. **Ensure Traefik can access the network**:
   Your Traefik container needs to be on the `traefik-network` network.

3. **Update labels** if needed:
   - Change `Host(\`stats.liveencode.com\`)` to your domain
   - Adjust middleware names if using different auth setup
   - Update certificate resolver if using different SSL setup

### Your Staging Environment

For your Pi400 staging environment with Traefik/Authelia:

```bash
# Make sure traefik-network exists
docker network ls | grep traefik-network

# If not, create it:
docker network create traefik-network

# Start with Traefik override
docker-compose -f docker-compose.yml -f docker-compose.traefik.yml up -d
```

Or if you prefer, uncomment the Traefik sections in `docker-compose.yml` directly.

### Verification

After starting with Traefik:
- Check container logs: `docker-compose logs admin`
- Verify Traefik routing: Check Traefik dashboard
- Access via your domain: `https://stats.liveencode.com`

---

**Note**: The base `docker-compose.yml` works standalone. Traefik configuration is optional and can be added via override file or by uncommenting the relevant sections.
