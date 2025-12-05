# Quick Fix: Use Database Backfill Script

Since frontend forward-fill isn't working, use the database backfill script:

## On Pi400:

```bash
cd /home/d2/stats
export $(grep -v '^#' .env | xargs)

# Dry run first (see what will be filled)
python3 scripts/forward_fill_historical_data.py --dry-run --interval 1

# Actually fix historical data
python3 scripts/forward_fill_historical_data.py --interval 1
```

This will permanently insert forward-filled values for all historical gaps.

## Why Frontend Forward-Fill Isn't Working

The backend generates time buckets, but there may be timestamp matching issues or the logic needs refinement. The database backfill is more reliable for fixing historical data.
