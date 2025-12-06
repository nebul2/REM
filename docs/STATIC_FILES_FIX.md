# Static Files Issue - Simple Fix

**Problem:** External auth service intercepts /static/ requests before they reach the app.

**Solution:** Configure the external auth service to allow /static/ paths to bypass authentication.

**Quick Test:**
- Static files work on localhost:7001 ✓
- External auth redirects /static/ requests to auth.liveencode.com ✗

**Fix Required:** 
Configure the external auth/proxy service to allow PathPrefix(`/static/`) to pass through without authentication.
