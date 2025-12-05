# Migration to TimescaleDB

## Why TimescaleDB?

Since Docker InfluxDB fails on ARM platforms, we're migrating to **TimescaleDB** - a PostgreSQL extension optimized for time-series data.

**Advantages**:
- ✅ Excellent Docker support (all platforms including ARM)
- ✅ Reliable initialization
- ✅ SQL-based queries (easier than Flux)
- ✅ Similar performance to InfluxDB
- ✅ Full PostgreSQL ecosystem

## Migration Plan

### 1. Database Schema

TimescaleDB uses standard PostgreSQL tables with hypertables:

```sql
CREATE TABLE gos_rem (
    time TIMESTAMPTZ NOT NULL,
    alias TEXT NOT NULL,
    power_watts DOUBLE PRECISION
);

SELECT create_hypertable('gos_rem', 'time');
```

### 2. Update Collector

Change from InfluxDB client to PostgreSQL client:
- Use `psycopg2` or `asyncpg` library
- Insert with: `INSERT INTO gos_rem (time, alias, power_watts) VALUES (...)`

### 3. Update Grafana

- Datasource: PostgreSQL (built-in)
- Queries: SQL instead of Flux
- Similar visualization capabilities

### 4. Docker Compose Changes

Replace InfluxDB service with:
```yaml
timescaledb:
  image: timescale/timescaledb:latest-pg16
  environment:
    POSTGRES_DB: gos_rem
    POSTGRES_USER: ${POSTGRES_USER:-gos}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  volumes:
    - timescaledb-data:/var/lib/postgresql/data
```

## Implementation Steps

1. Create TimescaleDB docker-compose service
2. Update collector.py to use PostgreSQL
3. Create database schema with hypertables
4. Update Grafana datasource configuration
5. Convert Grafana queries from Flux to SQL
6. Test on ARM platform

## Estimated Effort

- Database setup: 1 hour
- Collector migration: 2-3 hours
- Grafana queries: 2-3 hours
- Testing: 1 hour

**Total: 6-8 hours**

## Rollback Plan

If TimescaleDB doesn't work, we can:
- Try VictoriaMetrics (metrics-focused)
- Use standard PostgreSQL without TimescaleDB extension
- Document native InfluxDB requirement for ARM platforms

