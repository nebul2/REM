# Debug: Forward-Fill Not Working

## Problem

The frontend forward-fill is implemented but not working. Looking at the chart, totals still drop to 0 when devices fail.

## Analysis

### Current Implementation

1. **Backend** (admin/app.py line 325-336):
   - Already generates ALL time buckets (including empty ones) ✅
   - Sets missing devices to `None` ✅

2. **Frontend** (admin/static/exploration.js line 640-657):
   - Forward-fill logic exists ✅
   - Tracks last known values ✅
   - Should forward-fill when device is None ✅

### The Issue

Looking at the forward-fill logic more carefully:

```javascript
if (filledPoint[dev] !== null && filledPoint[dev] !== undefined && !isNaN(filledPoint[dev])) {
    // Update last known value
    lastKnownValues[dev] = filledPoint[dev];
} else if (lastKnownValues[dev] !== null) {
    // Forward-fill with last known value
    filledPoint[dev] = lastKnownValues[dev];
}
```

The problem: When `filledPoint[dev]` is `null` or `undefined`, it checks if `lastKnownValues[dev] !== null`. But `lastKnownValues[dev]` is initialized to `null` for each device. So if a device has never had a value, forward-fill can't work.

But more importantly: The logic only works if we iterate through data points in order. If time buckets are out of order, forward-fill won't work correctly.

Also: The backend might not be returning all time buckets if the data structure isn't set up correctly.

Let me check and fix the actual issue.

