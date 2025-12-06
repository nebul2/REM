# TimescaleDB Migration - COMPLETE ✅

## Overview

Complete migration from InfluxDB to TimescaleDB for fully portable Docker deployment.

## Status: ✅ ALL CHANGES COMPLETE

### 1. Docker Compose ✅
- ✅ Replaced `influxdb` service with `timescaledb` service
- ✅ Updated all environment variables from InfluxDB to PostgreSQL
- ✅ Added database initialization script
- ✅ All services now depend on TimescaleDB

### 2. Database Schema ✅
- ✅ Created `gos_rem` table with hypertable for time-series optimization
- ✅ Created indexes for performance (alias, time+alias)
- ✅ SQL initialization script: `scripts/init-timescaledb.sql`

### 3. Collector ✅
- ✅ Replaced `influxdb-client` with `psycopg2-binary`
- ✅ Changed from InfluxDB Point API to PostgreSQL INSERT
- ✅ Updated config.yaml to use PostgreSQL connection settings
- ✅ Batch insert using execute_values for efficiency

### 4. Admin UI ✅
- ✅ Replaced InfluxDBClient with PostgreSQL connection
- ✅ Converted Flux queries to SQL queries
- ✅ Updated device list query
- ✅ Updated power data query with time_bucket aggregation
- ✅ Updated requirements.txt

### 5. Grafana ✅
- ✅ Created PostgreSQL datasource configuration
- ✅ Note: Existing dashboards use Flux - will need to be rebuilt with SQL queries
- ✅ Datasource ready for new SQL-based dashboards

## SQL Query Examples

### Device List
```sql
SELECT DISTINCT alias 
FROM gos_rem 
WHERE time >= NOW() - INTERVAL '24 hours'
ORDER BY alias;
```

### Power Data Query (with aggregation)
```sql
SELECT 
  time_bucket('1 minute', time) AS time,
  alias,
  AVG(power_watts) AS power_watts
FROM gos_rem
WHERE time >= $1::timestamptz 
  AND time <= $2::timestamptz
  AND alias = ANY($3)
GROUP BY time_bucket('1 minute', time), alias
ORDER BY time, alias;
```

## Environment Variables

**Old (InfluxDB):**
- `INFLUXDB_URL`
- `INFLUXDB_ORG`
- `INFLUXDB_BUCKET`
- `INFLUXDB_TOKEN`

**New (PostgreSQL/TimescaleDB):**
- `POSTGRES_HOST` (default: `timescaledb`)
- `POSTGRES_PORT` (default: `5432`)
- `POSTGRES_DB` (default: `gos_rem`)
- `POSTGRES_USER` (default: `gos`)
- `POSTGRES_PASSWORD` (required)

## Files Changed

1. `docker-compose.yml` - TimescaleDB service
2. `scripts/init-timescaledb.sql` - Database schema
3. `app/collector.py` - PostgreSQL client
4. `app/config/config.yaml` - PostgreSQL config
5. `app/requirements.txt` - psycopg2-binary
6. `admin/app.py` - PostgreSQL queries
7. `admin/requirements.txt` - psycopg2-binary
8. `grafana/provisioning/datasources/postgresql.yml` - PostgreSQL datasource

## Next Steps

1. **Update ENV_TEMPLATE** with PostgreSQL variables
2. **Test on Pi400** - deploy and verify everything works
3. **Optional**: Migrate existing Grafana dashboards from Flux to SQL (or rebuild)

## Testing Checklist

- [ ] TimescaleDB container starts successfully
- [ ] Database schema initializes correctly (hypertable created)
- [ ] Collector writes data to TimescaleDB
- [ ] Admin UI can list devices
- [ ] Admin UI can query power data with time aggregation
- [ ] Grafana can connect to PostgreSQL datasource
- [ ] Data appears in admin UI charts
