# Traefik Setup for stats.liveencode.com

## Status

Traefik labels have been added to the admin service in `docker-compose.yml`. The service is configured to:

- Route `stats.liveencode.com` to the admin UI (port 7001)
- Use basic authentication with users: `admin` and `gos`
- Default password: `stats2024` (should be changed!)

## Traefik Configuration

The admin service has these Traefik labels:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.stats.rule=Host(`stats.liveencode.com`)"
  - "traefik.http.routers.stats.entrypoints=web"
  - "traefik.http.routers.stats.entrypoints=websecure"
  - "traefik.http.routers.stats.tls.certresolver=letsencrypt"
  - "traefik.http.services.stats.loadbalancer.server.port=7001"
  - "traefik.http.routers.stats.middlewares=stats-auth"
  - "traefik.http.middlewares.stats-auth.basicauth.usersfile=/etc/traefik/auth/users.txt"
  - "traefik.docker.network=traefik-network"
```

## Authentication

Users file is located at: `traefik-config/auth/users.txt`

Current users:
- `admin` - password: `stats2024`
- `gos` - password: `stats2024`

**⚠️ IMPORTANT: Change these passwords in production!**

To change passwords:
```bash
cd ~/stats
htpasswd -b traefik-config/auth/users.txt admin <newpassword>
htpasswd -b traefik-config/auth/users.txt gos <newpassword>
```

## Traefik Network

The service connects to `traefik-network` which should be connected to your Traefik container.

## If Traefik is Not Running

If you need to set up Traefik, it should:
1. Be connected to the `traefik-network`
2. Have access to `/var/run/docker.sock`
3. Have the auth file mounted: `./traefik-config/auth/users.txt:/etc/traefik/auth/users.txt`
4. Have port 80 and 443 exposed

## Testing

Once services are running:

1. Check Traefik can see the service:
   ```bash
   docker exec <traefik-container> cat /etc/traefik/traefik.yml
   ```

2. Test the route:
   ```bash
   curl -u admin:stats2024 http://stats.liveencode.com
   ```

3. Check HTTPS (if SSL is configured):
   ```bash
   curl -u admin:stats2024 https://stats.liveencode.com
   ```

## Troubleshooting

- **Service not appearing in Traefik**: Check that Traefik is on the same network (`traefik-network`)
- **Auth not working**: Verify the auth file path is correct in Traefik mount
- **DNS not resolving**: Check DNS settings point `stats.liveencode.com` to Pi400's IP

