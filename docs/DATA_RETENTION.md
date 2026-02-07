# Data Retention & Storage Limits

## Current Status

**Storage Usage:**
- Current database size: ~13 MB
- Total data points: ~20,000 rows
- Data range: December 4, 2025 to December 7, 2025 (3 days)
- Average growth rate: ~6.7 MB per day (at current polling interval of 10 seconds)

## Data Retention Policy

**Current Policy: UNLIMITED**
- No automatic data retention/deletion is configured
- All data is kept indefinitely until manually deleted
- TimescaleDB will continue storing data until disk space runs out

## Storage Estimates

Based on current usage:
- **1 day**: ~6.7 MB
- **7 days**: ~47 MB
- **30 days**: ~201 MB
- **90 days**: ~603 MB
- **1 year**: ~2.4 GB

**Note:** These estimates assume:
- ~33 devices being polled
- 10-second polling interval
- Each data point stores: timestamp, device alias, power (watts), metadata

## Recommended Retention Policy

If you want to limit storage growth, you can configure TimescaleDB retention policies:

### Option 1: 90-Day Retention (Recommended for Long-Term Analysis)
```sql
-- Add retention policy (delete data older than 90 days)
SELECT add_retention_policy('gos_rem', INTERVAL '90 days');
```

### Option 2: 30-Day Retention (Shorter-Term Analysis)
```sql
-- Add retention policy (delete data older than 30 days)
SELECT add_retention_policy('gos_rem', INTERVAL '30 days');
```

### Option 3: Manual Cleanup
```sql
-- Delete data older than specified date
DELETE FROM gos_rem WHERE time < NOW() - INTERVAL '90 days';
```

## Implementing Retention Policy

To add a retention policy:

1. **Connect to TimescaleDB:**
   ```bash
   docker exec -it stats-timescaledb psql -U gos -d gos_rem
   ```

2. **Add retention policy:**
   ```sql
   SELECT add_retention_policy('gos_rem', INTERVAL '90 days');
   ```

3. **Verify policy:**
   ```sql
   SELECT * FROM timescaledb_information.jobs;
   ```

## Disk Space Monitoring

Monitor database size:
```sql
SELECT pg_size_pretty(pg_database_size('gos_rem')) as db_size;
```

Monitor data range:
```sql
SELECT MIN(time) as oldest, MAX(time) as newest, COUNT(*) as total_rows 
FROM gos_rem;
```

## Considerations

1. **Experiment Snapshots**: Even if raw data is deleted, experiment snapshots and annotations are preserved (stored separately)

2. **Backup Strategy**: Consider regular backups before implementing retention policies

3. **Query Performance**: TimescaleDB automatically compresses old data, maintaining query performance even with large datasets

4. **Disk Space**: Monitor available disk space on the Pi400 (limited storage capacity)

## Current Configuration

- **New installs**: 90-day retention is enabled in `scripts/init-timescaledb.sql`.
- **Existing installs (e.g. Pi400)**: Run from the stats project root:
  ```bash
  ./scripts/retention-and-cleanup.sh
  ```
  This reports DB size, adds the 90-day policy if missing, and optionally deletes old data and runs `VACUUM FULL` to reclaim space. See also `tools/pi400/PI400_DISK_TIDY.md` for full Pi400 disk tidy steps.

