#!/bin/sh
# Manual InfluxDB initialization script
# Run this if automatic initialization fails

set -e

echo "Waiting for InfluxDB to be ready..."
for i in $(seq 1 60); do
    if wget -q --spider http://localhost:8086/health 2>/dev/null; then
        echo "✅ InfluxDB is ready!"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "❌ InfluxDB did not become ready in time"
        exit 1
    fi
    sleep 2
done

echo "Initializing InfluxDB..."
influx setup \
    --force \
    --username "${INFLUXDB_ADMIN_USER:-admin}" \
    --password "${INFLUXDB_ADMIN_PASSWORD}" \
    --org "${INFLUXDB_ORG:-GOS}" \
    --bucket "${INFLUXDB_BUCKET:-rem}" \
    --token "${INFLUXDB_TOKEN}" \
    --retention 90d

echo "✅ InfluxDB initialized successfully!"
