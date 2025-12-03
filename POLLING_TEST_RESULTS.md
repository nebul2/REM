# Polling Interval Test Results

## Critical Finding: Rate Limiting Detected! ⚠️

**We've already seen HTTP 429 (Too Many Requests) errors**, which indicates the TP-Link API has rate limits we need to respect.

### Rate Limit Errors Found:
- Total 429 errors seen: **5 errors**
- First detected: ~13:59 (at 30s interval)
- Latest: ~14:09 (during restart)

This suggests **even 30s interval may be pushing limits** with 34 devices.

---

## Test Plan

We'll test intervals systematically to find the maximum safe rate:

**Intervals to test:** 30s → 20s → 15s → 10s → 5s

**Current status:**
- ✅ Baseline (30s): Working, but saw rate limits
- 🔄 Testing 20s: In progress
- ⏳ 15s: Not tested
- ⏳ 10s: Not tested  
- ⏳ 5s: Not tested

---

## Test Results

### Interval: 30s (Baseline)
**Status:** ⚠️ **RATE LIMITS DETECTED**
- Devices: 34
- API calls per cycle: 35 (1 device list + 34 power reads)
- Calls per hour: ~4,200
- **Issues:** 5x HTTP 429 errors observed
- **Recommendation:** Not safe - need slower interval

### Interval: 20s
**Status:** 🔄 **TESTING NOW**
- Started: 14:10
- Expected calls/hour: ~6,300
- Monitoring for errors...

### Interval: 15s
**Status:** ⏳ **PENDING**

### Interval: 10s
**Status:** ⏳ **PENDING**

### Interval: 5s
**Status:** ⏳ **PENDING**

---

## API Call Calculations

For **34 devices**:
- **30s interval**: 35 calls/cycle × 120 cycles/hour = **4,200 calls/hour**
- **20s interval**: 35 calls/cycle × 180 cycles/hour = **6,300 calls/hour**
- **15s interval**: 35 calls/cycle × 240 cycles/hour = **8,400 calls/hour**
- **10s interval**: 35 calls/cycle × 360 cycles/hour = **12,600 calls/hour**
- **5s interval**: 35 calls/cycle × 720 cycles/hour = **25,200 calls/hour**

---

## Observations

### Rate Limit Behavior
- HTTP 429 errors occur during device power reads
- Errors are intermittent (not every call)
- Suggests rate limit window (e.g., per minute or per hour)
- Some devices succeed, others fail (throttling individual calls)

### Current Collection Pattern
1. Get device list (1 API call)
2. Loop through 34 devices:
   - Get power for each (34 API calls)
   - **Total: 35 API calls per cycle**

---

## Recommendations (Preliminary)

Based on initial findings:
- **30s interval**: Already seeing rate limits ❌
- **Safe interval**: Likely **45-60 seconds** or higher
- **Optimal interval**: Need to test slower intervals

### Next Steps:
1. ✅ Test 20s (current)
2. ⏳ If errors continue, test **45s** and **60s**
3. ⏳ Find the highest interval with **zero 429 errors**

---

## Testing Commands

### Monitor for Errors
```bash
# Watch logs in real-time
docker-compose logs -f collector | grep -E "(429|rate limit|error|WARNING)"

# Count rate limit errors
docker-compose logs collector | grep "429" | wc -l

# Check last errors
docker-compose logs collector | grep -iE "(429|rate limit)" | tail -10
```

### Change Interval
```bash
# Update .env
sed -i.bak 's/^POLL_INTERVAL=.*/POLL_INTERVAL=45/' .env

# Restart collector
docker-compose down collector
docker-compose up -d collector
```

### Check Current Status
```bash
# See current interval
docker-compose logs collector | grep "Poll interval" | tail -1

# Count successful collections
docker-compose logs --since 5m collector | grep "Collected.*W from" | wc -l
```

---

**Last Updated:** 2025-12-02 14:10
**Status:** Testing in progress


### Interval: 15s
**Status:** ⚠️ **1 RATE LIMIT ERROR**
- Test duration: 2 minutes
- Successful collections: 64 (in 2 min)
- Rate limit errors: 1
- Calls per hour: ~8,400
- **Verdict:** Seeing occasional rate limits - not optimal

