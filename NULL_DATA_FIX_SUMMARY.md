# Null Data Investigation - Complete Fix Summary

## Problem Identified ✅

**Symptom**: Total and Average dropping from ~90-95W to near 0W every ~2 minutes

**Root Cause**: 
- API calls are failing intermittently (likely rate limiting or timeouts)
- When devices fail, NO data is written for those devices
- Time bucket aggregation creates gaps (missing devices don't appear)
- Frontend treats missing devices as 0 → Total drops to 0

## Fix Implemented ✅

### Forward-Fill for Missing Values

I've added forward-fill logic to the frontend:
- When a device is missing from a time bucket, use the **last known value** instead of 0
- This stabilizes totals/averages when devices temporarily fail
- Applied to Total calculations in both single-chart and overlay modes

**Files Modified**:
- `admin/static/exploration.js` - Added forward-fill for Total calculations
- `app/collector.py` - Already has proper error handling (no changes needed)

## What This Fixes

**Before**: 
- Device fails → Missing from time bucket → Counted as 0 → Total drops

**After**:
- Device fails → Missing from time bucket → Uses last known value → Total stays stable

## Still Need to Check

1. **Collector Logs** - Check pi400 logs to see error patterns:
   ```bash
   ssh d2@pi400 'docker logs stats-collector --tail 200 | grep -i "failed\|error\|warning"'
   ```

2. **The ~2 Minute Pattern** - This suggests:
   - Rate limiting (most likely)
   - Token refresh causing temporary failures
   - Network timeouts
   - All devices failing simultaneously

3. **Forward-Fill for Averages** - Currently only implemented for Totals, may need for Averages too

## Next Steps

1. Deploy the forward-fill fix
2. Test if the ~2 minute drops still occur
3. Check collector logs to identify the failure pattern
4. Consider adjusting polling interval if rate limiting is the issue

The forward-fill should significantly improve chart stability and prevent the dramatic drops to 0.

