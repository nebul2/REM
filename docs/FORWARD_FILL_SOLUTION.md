# Forward-Fill Not Working - Solution

## The Problem

The frontend forward-fill logic exists but isn't working because:

1. **Backend time bucket generation** - Generates buckets but timestamps might not match TimescaleDB exactly
2. **Missing time buckets** - When ALL devices fail, time buckets might be completely missing from response
3. **Forward-fill limitations** - Can only fill existing data points, can't create new time buckets

## Best Solution: Use Database Backfill Script

Since the frontend forward-fill isn't working reliably, **use the database backfill script** to permanently fix historical data:

```bash
# On pi400
cd /home/d2/stats
export $(grep -v '^#' .env | xargs)

# Dry run first
python3 scripts/forward_fill_historical_data.py --dry-run

# Actually fix historical data
python3 scripts/forward_fill_historical_data.py
```

This will:
- Identify all gaps in historical data
- Insert forward-filled values (last known value)
- Permanently fix the database
- Make charts smooth going forward

## Alternative: Fix Frontend Forward-Fill

If you prefer to keep fixing at display time, we need to:
1. Ensure backend generates ALL time buckets matching TimescaleDB exactly
2. Improve frontend forward-fill to handle edge cases
3. Test thoroughly

But the database backfill script is simpler and more reliable for fixing historical data.

## Recommendation

**Use the database backfill script** - it's the most reliable way to fix historical data gaps permanently.

