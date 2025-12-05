# Pi400 Staging Environment Deployment

This guide is for deploying to the Pi400 staging environment which uses Traefik reverse proxy.

## Quick Start with Traefik

The base `docker-compose.yml` works standalone, but for your Pi400 environment with Traefik, you have two options:

### Option 1: Use Override File (Recommended)

```bash
cd ~/stats
docker-compose -f docker-compose.yml -f docker-compose.traefik.yml up -d
```

This uses the `docker-compose.traefik.yml` override file which adds Traefik configuration.

### Option 2: Uncomment Traefik Configuration

Edit `docker-compose.yml` and uncomment the Traefik sections:

1. In the `admin` service, uncomment:
   - The `traefik-network` network
   - The `labels` section

2. In the `networks` section, uncomment:
   - The `traefik-network` definition

Then just run:
```bash
docker-compose up -d
```

## Current Configuration

For your staging environment, you should uncomment these sections in `docker-compose.yml`:

**In admin service (around line 117-127):**
```yaml
networks:
  - stats-network
  - traefik-network  # Uncomment this line
labels:  # Uncomment this entire section
  - "traefik.enable=true"
  - "traefik.http.routers.stats.rule=Host(`stats.liveencode.com`)"
  - "traefik.http.routers.stats.entrypoints=websecure"
  - "traefik.http.routers.stats.tls.certresolver=letsencrypt"
  - "traefik.http.services.stats.loadbalancer.server.port=7001"
  - "traefik.http.routers.stats.middlewares=stats-auth"
  - "traefik.http.middlewares.stats-auth.basicauth.usersfile=/etc/traefik/auth/users.txt"
  - "traefik.docker.network=traefik-network"
```

**In networks section (around line 147):**
```yaml
networks:
  stats-network:
    driver: bridge
  traefik-network:  # Uncomment these two lines
    external: true
```

## After Making Changes

```bash
# Pull latest code
cd ~/stats
git pull

# Recreate containers with new config
docker-compose down
docker-compose up -d
```

## Verification

After starting:
- Check Traefik routing: `https://stats.liveencode.com`
- Verify containers: `docker-compose ps`
- Check logs: `docker-compose logs admin`

---

**Note**: The system works standalone for new users, but your staging environment needs the Traefik configuration uncommented.
