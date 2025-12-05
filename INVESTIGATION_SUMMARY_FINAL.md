# Null Data Investigation - Final Summary

## Problem

Total and Average lines drop from ~90-95W to near 0W every ~2 minutes, suggesting intermittent API failures causing data gaps.

## Root Cause Identified

1. **API calls failing intermittently** - Devices not responding every ~2 minutes (likely rate limiting or network timeouts)
2. **Collector correctly skips failed devices** - No invalid data written ✅
3. **Time bucket gaps created** - Missing devices don't appear in failed time buckets
4. **Frontend treats missing as 0** - Totals drop dramatically when devices fail

## Fix Implemented

### Forward-Fill for Missing Values ✅

I've added forward-fill logic to the frontend aggregation:
- When a device is missing from a time bucket, use the **last known value** instead of 0
- This stabilizes totals/averages when devices temporarily fail
- Applied to Total calculations (single chart and overlay modes)

### What Still Needs Checking

1. **Collector Logs**: Check pi400 to see error patterns:
   ```bash
   ssh d2@pi400 'docker logs stats-collector --tail 200 | grep -i "failed\|error\|warning"'
   ```

2. **The ~2 Minute Pattern**: This suggests:
   - Rate limiting (most likely)
   - Token refresh causing temporary failures
   - Network timeouts
   - All devices failing simultaneously

## Next Steps

1. **Deploy the forward-fill fix** - This should stabilize the totals
2. **Check collector logs** - See what errors are being logged
3. **Monitor the pattern** - See if the ~2 minute drops still occur after forward-fill
4. **Consider API rate limits** - May need to increase polling interval

The forward-fill fix should prevent the dramatic drops to 0. Totals will now use last known values for missing devices, making the chart more stable.

