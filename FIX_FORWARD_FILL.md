# Fix: Forward-Fill Not Working

## Problem

The frontend forward-fill isn't working because:

1. **Backend filters out empty time buckets** - When ALL devices are missing, that time bucket isn't returned at all
2. **Forward-fill needs data points** - If a time bucket doesn't exist, there's nothing to fill
3. **Missing buckets cause gaps** - The chart sees missing time buckets as gaps, not as points to fill

## Root Cause

Looking at `admin/app.py` line 302:
```python
# Only add if there's at least one non-None value for a device
if any(v is not None for k, v in point.items() if k != "timestamp"):
    data_points.append(point)
```

This means if ALL devices fail in a time bucket, that bucket is completely omitted from the response. The frontend never sees it, so forward-fill can't help.

## Solution

We need to generate ALL expected time buckets in the backend, even when devices are missing. This ensures:
- All time buckets exist in the response
- Forward-fill can work on complete time series
- Charts show continuous data

## Fix Options

### Option 1: Generate Time Buckets in Backend (Recommended)

Modify the SQL query to generate all time buckets using `generate_series` and LEFT JOIN with actual data.

### Option 2: Generate Time Buckets in Frontend

Generate all expected time buckets on the frontend and forward-fill into those.

### Option 3: Keep Current + Better Forward-Fill

Keep current approach but improve forward-fill to handle missing time buckets.

I'll implement Option 1 - it's the cleanest solution.

