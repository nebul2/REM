# Null Data Investigation - Findings & Fix

## Problem
Chart shows Total and Average dropping from ~90-95W to near 0W every ~2 minutes. This pattern suggests API calls are failing intermittently.

## Root Cause

### Issue 1: Collector Error Handling ✅ (Already Fixed)
The collector already has proper error handling:
- Returns `None` on API failure
- Skips failed devices (doesn't write invalid data)
- Logs failures

### Issue 2: Time Bucket Gaps ❌ (The Real Problem)
When API calls fail:
1. **No data is written** for failed devices at that timestamp
2. **Time bucket aggregation** (`time_bucket()`) means missing devices don't appear in that bucket
3. **Frontend aggregation** treats missing devices as 0 when calculating totals

**Example**:
- 4 devices: DR001 (5W), DR002 (5W), DR003-TV (85W), DR004 (5W)
- **Normal total**: 100W
- **If 3 devices fail in one time bucket**: Only TV has data (85W) → Total = 85W (OK)
- **If ALL devices fail**: No data → Total = 0W ❌ (This is what you're seeing)

### The ~2 Minute Pattern
This suggests:
- **Rate limiting**: TP-Link API might rate limit after X requests
- **Token refresh**: Access token might expire/refresh causing temporary failures
- **Network timeouts**: All devices timing out simultaneously
- **Batch failures**: All API calls failing together (network issue, API downtime)

## Solution

### Fix 1: Forward-Fill Missing Values (Frontend)
When a device is missing from a time bucket, use the **last known value** instead of 0.

### Fix 2: Better Logging (Collector)
Track and log API failures with timestamps to identify patterns.

### Fix 3: Handle Missing Devices Better
Only calculate totals/averages when we have data for expected devices, or use forward-fill.

## Immediate Actions

1. **Check collector logs** on pi400:
   ```bash
   docker logs stats-collector --tail 100 | grep -i "failed\|error\|warning"
   ```

2. **Query database** to see if there are time buckets with missing devices:
   ```sql
   SELECT 
     time_bucket('1 minute', time) AS bucket,
     COUNT(DISTINCT alias) AS device_count,
     COUNT(*) AS readings
   FROM gos_rem
   WHERE time >= NOW() - INTERVAL '1 hour'
   GROUP BY bucket
   ORDER BY bucket DESC;
   ```

3. **Implement forward-fill** in frontend to stabilize totals

Let me check the actual database to see what's happening, then implement the fix.

