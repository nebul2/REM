# Forward-Fill Historical Data

## Overview

This script identifies gaps in historical data (where devices are missing from time buckets) and inserts forward-filled values (last known value) to stabilize historical charts.

**⚠️ WARNING**: This creates "estimated" data points. The forward-filled values are not actual measurements, but interpolations based on the last known value.

## Two Approaches

### Option 1: Backfill Script (Modifies Database)

Use `forward_fill_historical_data.py` to permanently insert forward-filled values into the database.

**Pros:**
- Permanent fix - charts will always show smooth data
- No query-time overhead

**Cons:**
- Creates "fake" data in database
- Masks real data quality issues
- Cannot distinguish between real and forward-filled data (without adding a flag)

### Option 2: Query-Time Forward-Fill (Recommended)

Modify the SQL query to forward-fill at query time using window functions. This doesn't modify the raw data.

**Pros:**
- Keeps raw data intact
- Can distinguish between real and estimated data
- More flexible

**Cons:**
- Query-time overhead
- Requires query modification

## Usage

### Option 1: Backfill Script

```bash
# Dry run first (see what would be filled)
docker exec stats-timescaledb python3 /path/to/forward_fill_historical_data.py --dry-run

# Actually fill gaps
docker exec stats-timescaledb python3 /path/to/forward_fill_historical_data.py
```

Or run locally with database connection:

```bash
# Set environment variables
export POSTGRES_HOST=timescaledb
export POSTGRES_PORT=5432
export POSTGRES_DB=gos_rem
export POSTGRES_USER=gos
export POSTGRES_PASSWORD=your_password

# Dry run
python3 scripts/forward_fill_historical_data.py --dry-run --interval 1

# Actually fill (will prompt for confirmation)
python3 scripts/forward_fill_historical_data.py --interval 1
```

### Option 2: Query-Time Forward-Fill

The frontend already implements forward-fill in JavaScript. For historical data, we could also implement it in SQL, but the frontend approach is simpler and more flexible.

## Recommendation

**Use the frontend forward-fill (already implemented)** - This doesn't modify historical data and handles gaps gracefully at display time. The backfill script is available if you really want to modify historical data permanently.

