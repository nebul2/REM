# Investigation: Null/Missing Data Issue

## Problem Description

The chart shows that Total and Average lines drop from maximum (~90-95W) to near minimum (~0W) approximately every 2 minutes. This pattern suggests:

1. **API calls failing intermittently** - Devices not returning data periodically
2. **No error handling** - Failed API calls result in missing data points
3. **Time bucket aggregation gaps** - Missing devices in time buckets cause calculation issues

## Root Cause Analysis

### Issue 1: Collector Has No Error Handling

**File**: `app/collector.py`

**Line 79-87**: `getDevPower()` function has no error handling:
```python
def getDevPower(deviceId, accessToken):
    devPowerurl='...'
    getDevpowerlistdata={"method": "getDeviceRealTimeEnergy", "device": {"id": deviceId }}
    session = requests.Session()
    session.headers.update({'Content-Type': 'application/json'})
    devPowerlist = session.post(devPowerurl, json=getDevpowerlistdata)
    devPowerlistreturn=devPowerlist.json()['result']['powerWatts']  # ⚠️ No error handling!
    return devPowerlistreturn
```

**Problems**:
- If `session.post()` fails (network error, timeout, etc.), it will raise an exception
- If the response JSON doesn't have `['result']['powerWatts']`, it will raise KeyError
- If the API returns null/None, it will try to convert to float which could cause issues

**Line 96**: `getDevicePowerList()` calls `getDevPower()` without try/except:
```python
for item in deviceIdList:
    devPower = getDevPower(item['deviceId'], accessToken)  # ⚠️ No error handling!
    # ... continues even if this fails
```

### Issue 2: Missing Data in Time Buckets

**File**: `admin/app.py`

**Line 235-299**: `query_power_data()` uses `time_bucket()` aggregation:

```sql
SELECT 
  time_bucket(%s, time) AS time,
  alias,
  AVG(power_watts) AS power_watts
FROM gos_rem
WHERE time >= %s AND time <= %s AND alias = ANY(%s)
GROUP BY time_bucket(%s, time), alias
```

**Problem**: If a device has NO data for a particular time bucket (because the API call failed), that device won't appear in the results for that bucket. This creates gaps in the data.

**Line 299**: When organizing data:
```python
point[device] = matching[0]["value"] if matching else None
```

If a device has no data for a timestamp, it's set to `None`, but the frontend aggregation logic treats `None` differently than missing devices.

### Issue 3: Frontend Aggregation Logic

**File**: `admin/static/exploration.js`

**Line 642**: Total calculation:
```javascript
const sum = devices.reduce((acc, dev) => acc + (point[dev] || 0), 0);
```

**Problem**: If `point[dev]` is `None` (from backend), it uses 0. But if the device is completely missing from the data point (no key at all), it's not included in the reduce, causing the sum to drop.

**Example**:
- 4 devices expected: DR001, DR002, DR003, DR004
- TV (DR003) = 85W (always present)
- Others (DR001, DR002, DR004) = 5W each when present
- **Total when all present**: 85 + 5 + 5 + 5 = 100W
- **If 3 devices missing from time bucket**: Only TV = 85W
- **But if API calls fail and no data written**: Total = 0 (all missing)

## Solution

### Fix 1: Add Error Handling to Collector

1. Wrap API calls in try/except
2. Log errors but continue with other devices
3. Skip devices that fail (don't write null/0 values)
4. Or optionally write a sentinel value (like -1) to indicate failed reads

### Fix 2: Handle Missing Devices in Frontend

1. When calculating totals/averages, account for expected device count
2. Use last known value for missing devices (forward fill)
3. Or exclude time buckets where expected devices are missing

### Fix 3: Improve Data Quality

1. Add validation before writing to database
2. Log when devices fail to respond
3. Add monitoring/alerts for failed API calls

## Immediate Fix Needed

The collector needs error handling to:
1. Catch API failures gracefully
2. Continue polling other devices if one fails
3. Log failures for debugging
4. Not write null/0 values for failed devices

## Recommended Changes

1. **Add error handling to `getDevPower()`** - Return None on failure
2. **Add error handling to `getDevicePowerList()`** - Skip failed devices
3. **Add logging** - Track which devices fail and when
4. **Add validation** - Don't write invalid data to database
5. **Frontend handling** - Better handling of missing devices in aggregation

