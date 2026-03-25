# Testing Polling Intervals

## Goal
Find the maximum polling rate that doesn't trigger rate limiting or errors from the TP-Link API.

## Current Setup
- Default interval: **30 seconds**
- Number of devices: **34 devices**
- API calls per cycle: **35** (1 device list + 34 power readings)

## Test Plan

### Step-by-Step Testing

1. **Test current interval (30s)**
   ```bash
   ./test_polling_rate.sh 30
   ```
   Watch for 2-3 minutes. Look for any errors.

2. **Test faster intervals** (one at a time):
   ```bash
   ./test_polling_rate.sh 20
   ./test_polling_rate.sh 15
   ./test_polling_rate.sh 10
   ./test_polling_rate.sh 5
   ```

3. **Monitor for issues**:
   - Rate limit errors (HTTP 429)
   - API timeout errors
   - Failed token refresh
   - Missing device data

### Quick Test Commands

```bash
# Test 20 seconds
./test_polling_rate.sh 20

# Monitor logs directly
docker-compose logs -f collector | grep -E "(error|rate limit|Collected)"

# Check for errors in last 5 minutes
docker-compose logs --since 5m collector | grep -iE "(error|failed|429|rate limit)"
```

### What to Look For

**Good signs:**
- ✅ "Found X online P110 devices" appears regularly
- ✅ "Collected X.XW from DeviceName" messages
- ✅ No error messages
- ✅ Consistent data collection

**Bad signs:**
- ❌ "rate limit" or "429" errors
- ❌ "timeout" or connection errors
- ❌ Token refresh failures
- ❌ Fewer devices than expected
- ❌ Missing data points

### Manual Testing

You can also manually change the interval:

1. Edit `.env` file:
   ```bash
   POLL_INTERVAL=10  # Change this value
   ```

2. Restart collector:
   ```bash
   docker-compose restart collector
   ```

3. Monitor logs:
   ```bash
   docker-compose logs -f collector
   ```

4. Check for errors:
   ```bash
   docker-compose logs collector | grep -i error | tail -20
   ```

### Expected Results

**Conservative estimate:**
- **30s interval**: Safe, ~4,080 API calls/hour (34 devices × 120 calls/hour)
- **20s interval**: Likely safe, ~6,120 API calls/hour
- **15s interval**: Probably safe, ~8,160 API calls/hour
- **10s interval**: May hit limits, ~12,240 API calls/hour
- **5s interval**: Likely too fast, ~24,480 API calls/hour

### Recommendations

After testing, we'll know:
- **Safe interval**: Highest interval with zero errors
- **Optimal interval**: Balance between speed and reliability
- **Recommended interval**: Safe interval + 5-10s buffer

### Restore Default

To restore to default 30s interval:
```bash
sed -i.bak 's/^POLL_INTERVAL=.*/POLL_INTERVAL=30/' .env
docker-compose restart collector
```

## Benchmark (round time vs 10s target)

The collector sleeps **`poll_interval`** seconds **after** each full round (device list + every plug). Per-device sample spacing ≈ **round duration + poll_interval**.

From the repo root, with the stack running:

```bash
./scripts/run_benchmark_poll.sh --rounds 5
./scripts/run_benchmark_poll.sh --sweep --rounds 3 --target-cadence 10
```

This runs **`benchmark_poll_cycle.py`** inside the collector container (no DB writes). Use **`--sweep`** to try several `parallel_workers` values and pick the fastest mean round time, then set that value in the Exploration UI (or `COLLECTOR_PARALLEL_WORKERS`).

