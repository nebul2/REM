-- Initialize TimescaleDB schema for GOS REM system

-- Create database if it doesn't exist (run as postgres user)
-- CREATE DATABASE gos_rem;

-- Connect to gos_rem database
\c gos_rem;

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create table for power measurements
CREATE TABLE IF NOT EXISTS gos_rem (
    time TIMESTAMPTZ NOT NULL,
    alias TEXT NOT NULL,
    power_watts DOUBLE PRECISION NOT NULL
);

-- Create hypertable (TimescaleDB optimization for time-series data)
SELECT create_hypertable('gos_rem', 'time', if_not_exists => TRUE);

-- Create index on alias for faster filtering
CREATE INDEX IF NOT EXISTS idx_gos_rem_alias ON gos_rem (alias);

-- Create composite index for common queries (time + alias)
CREATE INDEX IF NOT EXISTS idx_gos_rem_time_alias ON gos_rem (time DESC, alias);

-- 90-day retention: drop old data automatically to avoid filling disk (e.g. on Pi400)
-- Wrapped in DO block so table creation is not rolled back if this fails (e.g. TimescaleDB version)
DO $$
BEGIN
  PERFORM add_retention_policy('gos_rem', INTERVAL '90 days');
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'Retention policy not added (optional): %', SQLERRM;
END $$;

