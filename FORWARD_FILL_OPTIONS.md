# Forward-Fill Options for Historical Data

## Quick Answer

**Yes!** You can correct historically collected data in the database using forward-fill. I've created a script for this, but there are two approaches:

## Option 1: Frontend Forward-Fill (Already Implemented) ✅

**Status**: Already working!

The frontend JavaScript already implements forward-fill at display time. This means:
- ✅ Historical gaps are filled automatically when viewing charts
- ✅ Raw data remains intact (no database modification)
- ✅ Works immediately for all historical data
- ✅ No setup required

**This is probably sufficient** - your charts should already show smooth totals without drops.

## Option 2: Database Backfill Script (Optional)

**Status**: Script created, ready to use!

If you want to permanently modify historical data in the database, use the backfill script:

### What It Does

1. Scans all historical time buckets
2. Identifies gaps where devices are missing
3. Inserts forward-filled values (last known value) for missing devices
4. Permanently modifies the database

### How to Use

**On Pi400:**

```bash
# SSH to pi400
ssh d2@pi400

# Navigate to project
cd /home/d2/stats

# Set environment variables from .env
export $(grep -v '^#' .env | xargs)

# Dry run first (see what would be filled - RECOMMENDED)
docker exec -it stats-admin python3 scripts/forward_fill_historical_data.py --dry-run --interval 1

# If dry run looks good, actually fill gaps
docker exec -it stats-admin python3 scripts/forward_fill_historical_data.py --interval 1
```

**From Your Local Machine:**

```bash
# Set database connection
export POSTGRES_HOST=pi400  # or the IP
export POSTGRES_PORT=5432
export POSTGRES_DB=gos_rem
export POSTGRES_USER=gos
export POSTGRES_PASSWORD=your_password

# Dry run
python3 scripts/forward_fill_historical_data.py --dry-run --interval 1

# Actually fill
python3 scripts/forward_fill_historical_data.py --interval 1
```

### Script Options

- `--dry-run`: Preview changes without modifying database (USE THIS FIRST!)
- `--interval MINUTES`: Time bucket size (default: 1 minute)
- `--max-lookback MINUTES`: How far back to look for last known value (default: 60)

## Which Should You Use?

### Use Frontend Forward-Fill (Option 1) If:
- ✅ You want to keep raw data intact
- ✅ You want to see when devices actually failed
- ✅ You're okay with gaps being filled at display time
- ✅ You want immediate results (already working!)

### Use Database Backfill (Option 2) If:
- ✅ You want permanently smooth historical data
- ✅ You're okay creating "estimated" data points
- ✅ You want database-level forward-fill

## Recommendation

**Try the frontend forward-fill first** - it's already implemented and working. If you still see drops or want to permanently modify historical data, then use the backfill script.

The frontend forward-fill should solve your chart stability issue without modifying your raw data!

