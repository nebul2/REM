## Decision: Move to Option 3

Docker InfluxDB fails on ARM platforms. Since Option 1 doesn't work and we're skipping Option 2, we're implementing **Option 3: Alternative Database**.

**Chosen Alternative**: TimescaleDB
- PostgreSQL-based time-series database
- Excellent Docker support
- Works on all platforms including ARM
- SQL queries (easier than Flux)

See MIGRATION_TO_TIMESCALEDB.md for full plan.
