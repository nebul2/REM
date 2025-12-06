# Quick Polling Interval Test Summary

## Current Status

**Testing:** 20 second interval
**Result:** ✅ No rate limit errors in last 2 minutes

## Test Process

I've created scripts to test different intervals systematically:

### Option 1: Manual Step-by-Step (Recommended)
Use the test script to change intervals one at a time:

```bash
# Test 15 seconds
./test_polling_rate.sh 15

# Monitor for 2-3 minutes, then try:
./test_polling_rate.sh 10
```

### Option 2: Automated Testing
Run the automated test (takes ~15-20 minutes):

```bash
./test_intervals_automated.sh
```

This will test: 30s → 20s → 15s → 10s → 5s

## Findings So Far

- **30s interval**: ⚠️ Saw 5 rate limit (429) errors
- **20s interval**: ✅ Testing now, no errors in last 2 minutes
- **Note**: Previous errors might have been from accumulated requests

## What to Look For

✅ **Good signs:**
- "Collected X.XW from DeviceName" messages
- No "429" or "rate limit" errors
- Consistent data collection

❌ **Bad signs:**
- HTTP 429 errors
- "Too Many Requests" messages
- Missing device data

## Current Recommendations

Based on findings:
- **30s**: Has seen rate limits, not recommended
- **20s**: Testing, looks promising so far
- **Next**: Test 15s, 10s to find sweet spot

## Quick Commands

```bash
# Check for errors right now
docker-compose logs --since 5m collector | grep -iE "(429|rate limit|error)"

# See current interval
docker-compose logs collector | grep "Poll interval" | tail -1

# Change to test interval (e.g., 15s)
sed -i.bak 's/^POLL_INTERVAL=.*/POLL_INTERVAL=15/' .env
docker-compose down collector && docker-compose up -d collector
```

