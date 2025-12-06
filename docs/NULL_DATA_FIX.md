# Fix for Null/Missing Data Issue

## Problem Summary

**Symptoms**: Total and Average lines drop from ~90-95W to near 0W every ~2 minutes

**Root Cause**: 
- API calls are failing intermittently (likely rate limiting or timeouts)
- When devices fail, NO data is written to database for that time bucket
- Frontend calculates totals with missing devices treated as 0, causing dramatic drops

## Investigation Findings

✅ **Collector Error Handling**: Already implemented - returns `None` on failure and skips failed devices
✅ **Logging**: Already logs failed devices
❌ **Frontend Aggregation**: Missing devices are treated as 0, causing total to drop

## The Real Issue

When devices fail API calls:
1. Collector correctly skips them (doesn't write invalid data) ✅
2. No data point exists for that device in that time bucket
3. Time bucket aggregation (`time_bucket()`) means missing devices don't appear
4. Frontend sees incomplete data and calculates:
   - If 1 device missing: Total drops slightly (e.g., 100W → 95W)
   - If ALL devices missing: Total = 0W ❌

## Solution

### Option 1: Forward-Fill Missing Values (Recommended)
When a device is missing from a time bucket, use the last known value instead of 0.

### Option 2: Better Error Tracking
Log and track API failures to identify patterns (rate limiting, network issues, etc.)

### Option 3: Database-Level Forward Fill
Use SQL `LAG()` or similar to forward-fill in the query itself.

## Immediate Action Needed

1. **Check collector logs** on pi400 to see:
   - Which devices are failing
   - When they fail (the ~2 minute pattern)
   - Error messages

2. **Implement forward-fill** in frontend to stabilize totals

3. **Monitor API rate limits** - The ~2 minute pattern suggests rate limiting

Let me implement the forward-fill fix now.

