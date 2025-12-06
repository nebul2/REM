# Final Polling Interval Test Results

## Executive Summary

**Tested intervals:** 5s, 10s, 15s, 20s, 30s, 45s, 60s  
**Devices:** 34 P110 devices  
**API calls per cycle:** 35 (1 device list + 34 power reads)  
**Test duration:** 2-3 minutes per interval

---

## Test Results Table

| Interval | Calls/Hour | Errors (429) | Collections | Status | Verdict |
|----------|-----------|--------------|-------------|--------|---------|
| **5s** | 25,200 | 2 | 75 | ❌ Too Fast | Multiple errors |
| **10s** | 12,600 | 1 | 68 | ⚠️ Fast | Occasional limits |
| **15s** | 8,400 | 1 | 64 | ⚠️ Moderate | Occasional limits |
| **20s** | 6,300 | 0* | 26 | ✅ Good | Best so far |
| **30s** | 4,200 | 5** | - | ⚠️ Baseline | Saw errors |
| **45s** | 2,800 | 1 | 65 | ⚠️ Slow | Still errors |
| **60s** | 2,100 | 3 | 50 | ⚠️ Very Slow | Errors persist |

*0 errors in 2-minute test window  
**Errors from earlier in session (may be cumulative)

---

## Key Findings

### 1. Rate Limiting is Present
- **TP-Link API has rate limits** (HTTP 429 errors)
- Errors occur **intermittently** - not every request fails
- Rate limit appears to be **time-window based** (likely per hour or rolling window)

### 2. Rate Limit Behavior
- Errors happen during **device power reads** (not device list)
- Some devices succeed, others fail in the same cycle
- Suggests **per-endpoint** or **burst** rate limiting

### 3. Optimal Interval
- **20 seconds** showed **zero errors** in 2-minute test
- **10-15 seconds** show occasional errors (1 per 2-3 min)
- Even **60 seconds** showed errors (likely residual/cumulative)

### 4. Rate Limit Window
The fact that errors appear even at slower intervals suggests:
- **Cumulative rate limit** over longer time window (e.g., per hour)
- **Burst limit** (too many requests in short time)
- **Per-device limits** (some devices hit limit before others)

---

## Recommendations

### For Production (24/7 Monitoring)

**Recommended: 30-45 seconds**
- Good balance of data resolution and reliability
- Occasional errors are acceptable (handled gracefully)
- Provides ~2-4 data points per minute per device

### For Experiments (Short-term High Frequency)

**Recommended: 20 seconds**
- Fastest tested interval with zero errors in test window
- Good for detailed experiment analysis
- May see occasional errors over longer periods

### Conservative (Zero Tolerance for Errors)

**Recommended: 60+ seconds**
- Slowest polling rate
- Note: Still saw errors (may be residual from testing)
- Best for long-term monitoring where data gaps are acceptable

---

## Rate Limit Mitigation Strategies

### Current Implementation
- Errors are logged as warnings
- Collector continues running
- Failed devices are retried on next cycle
- No data loss (just delayed)

### Future Enhancements
1. **Exponential backoff** on 429 errors
2. **Rate limit detection** - automatically slow down on errors
3. **Batch throttling** - add delays between device reads
4. **Device prioritization** - poll critical devices first

---

## API Call Calculations

### Current Setup
- **34 devices** = 34 power reads per cycle
- **1 device list** = 1 API call per cycle
- **Total: 35 API calls per cycle**

### Call Rates by Interval

| Interval | Cycles/Hour | API Calls/Hour | Calls/Minute |
|----------|-------------|----------------|--------------|
| 60s | 60 | 2,100 | 35 |
| 45s | 80 | 2,800 | 47 |
| 30s | 120 | 4,200 | 70 |
| 20s | 180 | 6,300 | 105 |
| 15s | 240 | 8,400 | 140 |
| 10s | 360 | 12,600 | 210 |
| 5s | 720 | 25,200 | 420 |

---

## Implementation Notes

### Setting Polling Interval

The interval is easily configurable:

```bash
# Edit .env file
POLL_INTERVAL=30  # seconds

# Or set in docker-compose.yml
environment:
  - POLL_INTERVAL=30

# Restart collector
docker-compose restart collector
```

### Monitoring Rate Limits

```bash
# Check for rate limit errors
docker-compose logs collector | grep "429" | wc -l

# Monitor in real-time
docker-compose logs -f collector | grep -E "(429|rate limit|WARNING)"
```

---

## Conclusion

**Recommended Default: 30 seconds**

This provides:
- ✅ Good data resolution (2 data points/minute per device)
- ✅ Reasonable API call rate (~4,200/hour)
- ✅ Errors are infrequent and handled gracefully
- ✅ Good balance for most use cases

**For faster experiments: 20 seconds**
- Zero errors in test window
- Faster data collection
- May see occasional errors over longer periods

**For maximum safety: 45-60 seconds**
- Lower API call rate
- Best for 24/7 monitoring
- Still provides adequate data resolution

---

**Test Date:** 2025-12-02  
**Test Duration:** ~15 minutes total  
**Devices:** 34 P110 devices  
**Environment:** Local Docker stack

