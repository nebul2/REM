# Forward-Fill Historical Data

## Overview

Yes! You can correct historically collected data in the database using forward-fill. I've created a script that will:

1. **Identify gaps** - Find time buckets where devices are missing
2. **Forward-fill** - Insert the last known value for each missing device
3. **Stabilize charts** - Historical data will show smooth totals instead of drops

## ⚠️ Important Considerations

### Pros
- ✅ Permanent fix - charts will always show smooth data
- ✅ No query-time overhead
- ✅ Historical data looks complete

### Cons
- ⚠️ Creates "estimated" data points (not actual measurements)
- ⚠️ Masks real data quality issues
- ⚠️ Cannot distinguish between real and forward-filled data

### Recommendation

**The frontend already implements forward-fill** (we just added it). This means:
- Historical data gaps are handled at display time
- Raw data remains intact
- You can still see when devices actually failed

**Use the backfill script only if** you want to permanently modify historical data for smoother charts.

## Usage

### Option 1: Run via Docker (Recommended)

```bash
# Copy script to pi400
scp scripts/forward_fill_historical_data.py d2@pi400:/home/d2/stats/scripts/

# SSH to pi400
ssh d2@pi400

# Navigate to project
cd /home/d2/stats

# Run dry-run first (see what would be filled)
docker exec -it stats-timescaledb python3 -c "
import sys
sys.path.insert(0, '/tmp')
" || true

# Better: Run from local machine with database connection
# Set environment variables first
export POSTGRES_HOST=pi400  # or timescaledb if running locally
export POSTGRES_PORT=5432
export POSTGRES_DB=gos_rem
export POSTGRES_USER=gos
export POSTGRES_PASSWORD=your_password

# Dry run (shows what would be filled without modifying)
python3 scripts/forward_fill_historical_data.py --dry-run --interval 1

# Actually fill gaps (will prompt for confirmation)
python3 scripts/forward_fill_historical_data.py --interval 1
```

### Option 2: Run Directly on Pi400

```bash
# SSH to pi400
ssh d2@pi400

# Navigate to project
cd /home/d2/stats

# Install dependencies if needed (should already be in container)
# The script uses psycopg2 which is already installed

# Set environment variables from .env file
export $(grep -v '^#' .env | xargs)

# Dry run
python3 scripts/forward_fill_historical_data.py --dry-run --interval 1

# Actually fill
python3 scripts/forward_fill_historical_data.py --interval 1
```

### Option 3: Run from Admin Container

```bash
# Copy script into admin container
docker cp scripts/forward_fill_historical_data.py stats-admin:/tmp/

# Execute in container
docker exec -it stats-admin python3 /tmp/forward_fill_historical_data.py --dry-run

# Set environment variables in container
docker exec -it stats-admin env POSTGRES_HOST=timescaledb POSTGRES_DB=gos_rem POSTGRES_USER=gos POSTGRES_PASSWORD=your_password python3 /tmp/forward_fill_historical_data.py --dry-run
```

## Script Options

```bash
python3 scripts/forward_fill_historical_data.py [OPTIONS]

Options:
  --dry-run              Show what would be filled without inserting (RECOMMENDED FIRST)
  --interval MINUTES     Time bucket interval in minutes (default: 1)
  --max-lookback MINUTES Maximum minutes to look back for last known value (default: 60)
```

## Example Output

```
============================================================
Forward-Fill Historical Data Tool
============================================================

🔍 DRY RUN MODE - No data will be modified

Analyzing data from 2025-12-01 10:00:00 to 2025-12-05 22:00:00
Looking for gaps in 4 devices with 1-minute buckets
Found 142 time buckets with missing devices

Gap summary:
  Time buckets with gaps: 142

First 5 gaps:
  2025-12-05T21:15:00+00:00: Missing 3 devices (DR001-id3as, DR002-WRX, DR004-P1400)
  2025-12-05T21:16:00+00:00: Missing 3 devices (DR001-id3as, DR002-WRX, DR004-P1400)
  ...

[DRY RUN] Would insert 426 forward-filled data points

First 10 inserts:
  1. DR001-id3as at 2025-12-05 21:15:00: 5.2W (from 2025-12-05 21:14:00)
  2. DR002-WRX at 2025-12-05 21:15:00: 4.8W (from 2025-12-05 21:14:00)
  ...

[DRY RUN] To actually fill gaps, run without --dry-run flag
```

## How It Works

1. **Find Gaps**: Identifies time buckets where devices are missing
2. **Look Back**: For each gap, finds the last known value (within max-lookback window)
3. **Insert**: Inserts forward-filled values at the bucket time
4. **Preserve**: Uses `ON CONFLICT DO NOTHING` to avoid overwriting real data

## Limitations

- Only looks back up to `--max-lookback` minutes (default 60)
- If a device has no data for more than the lookback window, it won't be filled
- Creates estimated data that might not reflect actual device state

## Alternative: Frontend Forward-Fill (Recommended)

The frontend already implements forward-fill at display time. This means:
- ✅ No database modification needed
- ✅ Raw data remains intact
- ✅ Can see actual gaps if needed
- ✅ Works for all historical data automatically

**The frontend forward-fill is probably sufficient** - use the backfill script only if you want to permanently modify historical data.

