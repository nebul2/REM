# Investigation Complete: Null Data Drops

## Problem Summary

Your chart shows Total and Average dropping from ~90-95W to near 0W every ~2 minutes. This indicates **intermittent API failures** causing data gaps.

## Root Cause

### What's Happening
1. **API calls failing intermittently** - Devices not responding every ~2 minutes
2. **Collector correctly skips failed devices** - No invalid data written ✅
3. **Time bucket gaps** - Missing devices don't appear in failed time buckets
4. **Frontend treats missing as 0** - Totals drop dramatically when devices fail

### The ~2 Minute Pattern Suggests
- **Rate limiting** - TP-Link API might be rate limiting after X requests
- **Token refresh issues** - Access token might expire/refresh causing gaps
- **Network timeouts** - All devices timing out simultaneously
- **Batch failures** - All API calls failing together

## Current Code Status

✅ **Collector has error handling** - Already implemented
- Returns `None` on failure
- Skips failed devices (doesn't write invalid data)
- Logs warnings for failed devices

❌ **Frontend aggregation issue** - Missing devices treated as 0
- Line 642: `const sum = devices.reduce((acc, dev) => acc + (point[dev] || 0), 0);`
- When `point[dev]` is `undefined` (device missing from time bucket), it uses 0
- When ALL devices fail in a bucket, total = 0

## Recommended Fixes

### Fix 1: Forward-Fill Missing Values (Immediate)
When a device is missing from a time bucket, use the **last known value** instead of 0.

### Fix 2: Check Collector Logs
Review logs on pi400 to identify the failure pattern:
```bash
docker logs stats-collector --tail 200 | grep -i "failed\|error\|warning"
```

### Fix 3: Monitor API Rate Limits
Check if the ~2 minute pattern correlates with rate limiting.

## Next Steps

1. **Check logs first** - See what errors are being logged
2. **Implement forward-fill** - Stabilize totals when devices are missing
3. **Add monitoring** - Track API success/failure rates over time

Would you like me to:
- A) Implement the forward-fill fix immediately
- B) First check the collector logs on pi400 to see what errors are happening
- C) Both - check logs AND implement forward-fill

