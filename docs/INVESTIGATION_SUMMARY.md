# Investigation Summary: Null Data Drops

## Problem
Chart shows Total and Average dropping from ~90-95W to near 0W every ~2 minutes. Pattern suggests API calls are failing intermittently, causing data gaps.

## Root Cause Analysis

### Issue 1: Missing Error Handling in Collector (FIXED)
**Status**: ✅ Already fixed in current code
- Collector now has error handling and returns `None` on failure
- Failed devices are skipped (not written to database)
- Logging added for failed devices

### Issue 2: Time Bucket Gaps
**Problem**: When devices fail API calls:
- No data point is written to database for that device at that time
- Time bucket aggregation (`time_bucket()`) means missing devices don't appear in that bucket
- Frontend sees incomplete data and calculates totals/averages with available devices only

**Example**:
- 4 devices: DR001 (5W), DR002 (5W), DR003-TV (85W), DR004 (5W)
- Normal total: 100W
- If 3 devices fail: Only TV (85W) has data → Total = 85W ✅
- If ALL devices fail: No data → Total = 0W ❌ (this is what you're seeing)

### Issue 3: Frontend Aggregation
**Current logic** (line 642):
```javascript
const sum = devices.reduce((acc, dev) => acc + (point[dev] || 0), 0);
```

**Problem**: 
- If `point[dev]` is `undefined` (device missing from time bucket), it uses 0
- But if the device key doesn't exist at all, it might not be included
- When ALL devices are missing from a time bucket, total = 0

## The ~2 Minute Pattern

This suggests:
1. **Rate limiting** - TP-Link API might be rate limiting after X requests
2. **Token refresh** - Access token might be expiring/refreshing
3. **Network timeouts** - All devices timing out simultaneously
4. **API errors** - All API calls failing together

## Next Steps

1. **Check collector logs** on pi400 to see:
   - Which devices are failing
   - When they fail (timing pattern)
   - Error messages

2. **Improve frontend** to handle missing devices better:
   - Forward-fill last known value
   - Or show gaps clearly
   - Track expected device count

3. **Add monitoring** to track API success/failure rates

Let me check the collector logs and improve the aggregation logic.

