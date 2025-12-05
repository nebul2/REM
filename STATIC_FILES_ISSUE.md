# Static Files Authentication Issue

## Problem
Static files (CSS, JS, images) are being intercepted by an external authentication service (`auth.liveencode.com`) when accessed through `stats.liveencode.com`. The files work correctly when accessed directly via `localhost:7001`.

## Error Messages
- CSS files: MIME type 'application/json' instead of 'text/css'
- Images: 404 Not Found
- JavaScript: MIME type 'application/json' instead of 'application/javascript'

## Root Cause
An external authentication proxy is intercepting ALL requests to `stats.liveencode.com` before they reach the application's Traefik router. This is a global middleware that we cannot control from this project.

## Current Configuration
- Static files router has priority 10 (higher than main route priority 1)
- Static files route does NOT have auth middleware attached
- FastAPI serves static files correctly on localhost:7001

## Solution Options

### Option 1: Configure External Auth Service (Recommended)
If you have access to the external auth service configuration, add an exception for `/static/` paths:
```
PathPrefix(`/static/`) → bypass auth
```

### Option 2: Serve Static Files from CDN
- Move static files to a CDN (e.g., Cloudflare, AWS CloudFront)
- Update HTML to reference CDN URLs
- CDN URLs won't require authentication

### Option 3: Serve Static Files from Different Subdomain
- Create `static.stats.liveencode.com` subdomain
- Configure it to bypass authentication
- Update HTML to use subdomain for static assets

### Option 4: Embed Critical CSS Inline (Temporary)
- Embed critical CSS directly in HTML `<style>` tags
- Keep images/JS on separate domain or CDN

## Immediate Action Required
Contact the administrator of the external authentication service (`auth.liveencode.com`) to add an exception for `/static/*` paths on `stats.liveencode.com`.
