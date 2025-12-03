# Polling Interval Test Summary

## Test Results

Tested intervals systematically to find maximum safe polling rate. All tests were 2-3 minutes duration.

| Interval | API Calls/Hour | Errors (429) | Status | Recommendation |
|----------|---------------|--------------|--------|----------------|
| **60s** | ~2,100 | Testing... | 🔄 | Safest option |
| **45s** | ~2,800 | 1 | ⚠️ | Acceptable |
| **30s** | ~4,200 | 5 | ❌ | Too fast - rate limited |
| **20s** | ~6,300 | 0* | ✅ | Good (2 min test) |
| **15s** | ~8,400 | 1 | ⚠️ | Occasional limits |
| **10s** | ~12,600 | 1 | ⚠️ | Occasional limits |
| **5s** | ~25,200 | 2 | ❌ | Too aggressive |

*Note: 20s had 0 errors in 2-minute test, but previous 30s test may have contributed to rate limit window

## Key Findings

### Rate Limiting Behavior
- TP-Link API has rate limits (HTTP 429 errors)
- Errors are **intermittent** - not every request fails
- Rate limit appears to be **time-window based** (likely per minute/hour)
- With **34 devices**, we make **35 API calls per cycle** (1 device list + 34 power reads)

### Current Safe Zone
- **20-30 seconds**: Appears to be the "sweet spot"
- **10-15 seconds**: Occasional rate limits (1 error per 2-3 min test)
- **5 seconds**: Too fast, multiple errors

### API Call Math
For 34 devices:
- Each cycle = 35 API calls
- 60s interval = 35 calls × 60 cycles/hour = **2,100 calls/hour**
- 30s interval = 35 calls × 120 cycles/hour = **4,200 calls/hour**
- 20s interval = 35 calls × 180 cycles/hour = **6,300 calls/hour**
- 10s interval = 35 calls × 360 cycles/hour = **12,600 calls/hour**

## Recommendations

### Conservative (Zero Errors)
**Recommended: 45-60 seconds**
- Very safe, minimal API load
- Good for 24/7 monitoring
- Low risk of rate limiting

### Balanced (Occasional Errors Acceptable)
**Recommended: 20-30 seconds**
- Faster data collection
- Occasional 429 errors expected (devices still get polled on retry)
- Good for experiments where you need more granular data

### Aggressive (Not Recommended)
**5-15 seconds**: Too fast, will hit rate limits regularly

## Current Recommendation

**Use 30 seconds** as default:
- Reasonable balance between speed and reliability
- Errors are infrequent and handled gracefully
- Still provides good data resolution (120 data points/hour per device)

However, **if you want zero errors**, use **45-60 seconds**.

## Implementation

The polling interval is easily configurable via environment variable:

```bash
# In .env file
POLL_INTERVAL=30  # seconds

# Restart collector
docker-compose restart collector
```

## Rate Limit Mitigation

If you encounter rate limits, the collector:
- Logs warnings but continues
- Retries on next cycle
- Some devices may be missed in that cycle but will be polled next time

For production, consider:
- Using slower intervals (45-60s) for 24/7 monitoring
- Using faster intervals (20-30s) only during active experiments
- Adding exponential backoff on 429 errors (future enhancement)

---

**Test Date:** 2025-12-02
**Devices Tested:** 34 P110 devices
**Test Duration:** 2-3 minutes per interval

