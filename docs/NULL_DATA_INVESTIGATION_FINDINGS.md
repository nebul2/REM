# Null Data Investigation - Complete Findings

## Problem Identified

**Symptom**: Total and Average lines drop from ~90-95W to near 0W every ~2 minutes

**Root Cause**: API calls are failing intermittently, creating gaps in time buckets. When devices fail:
1. No data is written for failed devices (correct behavior - collector skips them)
2. Time bucket aggregation means missing devices don't appear in that bucket
3. Frontend calculates totals with missing devices = 0, causing dramatic drops

## What's Already Fixed

✅ **Collector Error Handling**: Already implemented
- Returns `None` on API failure
- Skips failed devices (doesn't write invalid data)
- Logs warnings for failed devices
- Has timeout protection (10 seconds)

## The Real Issue

### Problem 1: Time Bucket Gaps
When devices fail API calls:
- No data point exists for that device at that timestamp
- SQL `time_bucket()` aggregation means the device doesn't appear in that time bucket
- Frontend sees incomplete data for that timestamp

### Problem 2: Frontend Aggregation
Current logic (line 642):
```javascript
const sum = devices.reduce((acc, dev) => acc + (point[dev] || 0), 0);
```

When `point[dev]` is `undefined` (device missing from time bucket):
- Uses `|| 0` which makes it 0
- If ALL devices fail in a time bucket: Total = 0 ❌

### The ~2 Minute Pattern

This suggests:
- **Rate Limiting**: TP-Link API might be rate limiting after X requests
- **Token Refresh**: Access token might expire/refresh causing temporary failures
- **Network Timeouts**: All devices timing out simultaneously
- **Batch Failures**: All API calls failing together

## Solution Implemented

### Forward-Fill for Missing Values

I've implemented forward-fill logic:
- When a device is missing from a time bucket, use the **last known value** instead of 0
- This stabilizes totals/averages when devices temporarily fail
- Applied to both single-chart and overlay-chart modes

### What Needs Checking

1. **Collector Logs**: Check pi400 logs to see error patterns:
   ```bash
   ssh d2@pi400 'docker logs stats-collector --tail 200 | grep -i "failed\|error\|warning"'
   ```

2. **Database Query**: Check if there are time buckets with missing devices:
   ```sql
   SELECT 
     time_bucket('1 minute', time) AS bucket,
     COUNT(DISTINCT alias) AS device_count,
     MIN(time) AS first_reading,
     MAX(time) AS last_reading
   FROM gos_rem
   WHERE time >= NOW() - INTERVAL '2 hours'
   GROUP BY bucket
   ORDER BY bucket DESC
   LIMIT 20;
   ```

3. **API Rate Limits**: Check TP-Link API documentation for rate limits

## Next Steps

1. **Deploy the forward-fill fix** - This will stabilize totals when devices fail
2. **Check collector logs** - Identify the failure pattern
3. **Monitor API rate limits** - Adjust polling interval if needed
4. **Consider retry logic** - Add retry for failed API calls

The forward-fill fix should resolve the dramatic drops you're seeing. The totals will now use the last known value for missing devices instead of dropping to 0.

