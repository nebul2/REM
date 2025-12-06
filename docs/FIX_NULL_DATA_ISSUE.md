# Fix for Null/Missing Data Issue

## Problem Identified

Looking at your chart, the Total and Average lines are dropping from ~90-95W to near 0W every ~2 minutes. This indicates:

1. **API calls failing intermittently** - Devices not returning data periodically
2. **Time bucket gaps** - When devices fail, they have no data for that time bucket
3. **Frontend aggregation** - Missing devices cause totals/averages to drop dramatically

## Root Cause

### Issue 1: Time Bucket Aggregation Gaps

The SQL query groups data by time buckets (1 minute intervals):

```sql
SELECT 
  time_bucket('1 minute', time) AS time,
  alias,
  AVG(power_watts) AS power_watts
FROM gos_rem
WHERE time >= %s AND time <= %s AND alias = ANY(%s)
GROUP BY time_bucket('1 minute', time), alias
```

**Problem**: If a device has NO data for a time bucket (because the API call failed), that device doesn't appear in the results for that bucket at all. This creates gaps.

### Issue 2: Frontend Aggregation Logic

In `exploration.js`, line 642:

```javascript
const sum = devices.reduce((acc, dev) => acc + (point[dev] || 0), 0);
```

**Problem**: If `point[dev]` is `undefined` (device not in this time bucket), the `|| 0` makes it 0, which is correct. BUT if ALL devices except one are missing, the total drops dramatically.

**Example scenario**:
- 4 devices expected: DR001 (5W), DR002 (5W), DR003-TV (85W), DR004 (5W)
- Normal total: 100W
- If 3 devices fail API calls in one time bucket:
  - Only DR003-TV has data: 85W
  - But the frontend might be calculating based on only available devices
  - Or the time bucket has NO data for the failed devices (missing entirely)

### Issue 3: Collector Error Handling

The collector now has error handling (returns None on failure), but when a device fails:
- No data point is written to the database for that device at that time
- This creates gaps in time buckets
- Frontend sees missing devices and calculates totals/averages with available devices only

## Solution

### Fix 1: Forward-Fill Missing Devices in Frontend

When a device is missing from a time bucket, use the last known value (forward-fill) instead of treating it as 0 or null.

### Fix 2: Improve Time Bucket Query

Use COALESCE or fill gaps in SQL query to handle missing devices better.

### Fix 3: Better Error Logging

Track which devices fail and when, so we can identify patterns (rate limiting, network issues, etc.)

## Immediate Fix Needed

The frontend aggregation should:
1. Track expected device count
2. Use forward-fill for missing devices (carry forward last known value)
3. Or clearly indicate when devices are missing vs. actually at 0W

Let me implement a fix for the frontend aggregation to handle missing devices better.

