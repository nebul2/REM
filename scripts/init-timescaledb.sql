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

-- Set retention policy (optional - delete data older than 90 days)
-- This can be configured later via TimescaleDB retention policies

