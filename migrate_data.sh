#!/bin/bash
# Migrate data from old InfluxDB to new Docker-based InfluxDB

set -e

echo "=== InfluxDB Data Migration Script ==="
echo ""

OLD_TOKEN="gwTu1qAtPgIRU8eWNpLXuz92pKo6_lgV7Y4mhdMM7n_XOe-fTXts7T54P_FQJ69UMVuTyhr77Ly7XCGz9QUNAA=="
OLD_ORG="GOS"
OLD_BUCKET="rem"
OLD_HOST="http://localhost:8086"

# Check if old InfluxDB is accessible
echo "1. Checking old InfluxDB..."
if ! influx query "from(bucket:\"${OLD_BUCKET}\") |> range(start: -1h) |> count()" \
    --org "${OLD_ORG}" \
    --token "${OLD_TOKEN}" \
    --host "${OLD_HOST}" > /dev/null 2>&1; then
    echo "⚠️  Old InfluxDB not accessible. Starting it..."
    sudo systemctl start influxdb
    sleep 5
fi

# Check data exists
echo "2. Checking for existing data..."
DATA_COUNT=$(influx query "from(bucket:\"${OLD_BUCKET}\") |> range(start: -90d) |> count()" \
    --org "${OLD_ORG}" \
    --token "${OLD_TOKEN}" \
    --host "${OLD_HOST}" 2>/dev/null | grep -o '[0-9]\+' | head -1 || echo "0")

if [ "$DATA_COUNT" = "0" ] || [ -z "$DATA_COUNT" ]; then
    echo "ℹ️  No data found in old database or unable to query"
    exit 0
fi

echo "   Found data points: $DATA_COUNT"

# Export data using influx write (line protocol)
echo "3. Exporting data from old database..."
EXPORT_DIR="$HOME/backups/influxdb-export"
mkdir -p "$EXPORT_DIR"

# Export using influx query to line protocol format
influx query "from(bucket:\"${OLD_BUCKET}\") |> range(start: -90d)" \
    --org "${OLD_ORG}" \
    --token "${OLD_TOKEN}" \
    --host "${OLD_HOST}" \
    --raw > "$EXPORT_DIR/data-export.txt" 2>&1

if [ $? -eq 0 ] && [ -s "$EXPORT_DIR/data-export.txt" ]; then
    echo "✅ Data exported to $EXPORT_DIR/data-export.txt"
    
    # Check file size
    FILE_SIZE=$(du -h "$EXPORT_DIR/data-export.txt" | cut -f1)
    echo "   Export size: $FILE_SIZE"
    
    # Check if new InfluxDB is running
    if docker ps | grep -q stats-influxdb; then
        echo ""
        echo "4. New InfluxDB is running. Importing data..."
        
        # Get new InfluxDB token from .env or use default
        NEW_TOKEN=$(grep INFLUXDB_TOKEN ~/stats/.env | cut -d'=' -f2 | tr -d '"' || echo "")
        NEW_ORG="GOS"
        NEW_BUCKET="rem"
        
        if [ -z "$NEW_TOKEN" ]; then
            echo "⚠️  New InfluxDB token not found in .env"
            echo "   Please set INFLUXDB_TOKEN in ~/stats/.env and run this script again"
            exit 1
        fi
        
        # Import data (this requires line protocol format)
        # Note: influx write expects line protocol, not CSV
        echo "   Importing to new database..."
        
        # Convert and import - this is tricky, may need manual intervention
        echo "   ⚠️  Automatic import may require data format conversion"
        echo "   Export file saved at: $EXPORT_DIR/data-export.txt"
        echo ""
        echo "   To import manually, you may need to:"
        echo "   1. Convert export to line protocol format"
        echo "   2. Use: influx write -b rem -o GOS -t \$TOKEN -f export.txt"
        
    else
        echo ""
        echo "ℹ️  New InfluxDB not running yet"
        echo "   Start it with: cd ~/stats && docker-compose up -d influxdb"
        echo "   Then re-run this script to import"
    fi
    
else
    echo "⚠️  Export failed or produced empty file"
    echo "   Trying alternative export method..."
    
    # Alternative: Use influx backup (if available)
    if command -v influx backup &> /dev/null; then
        echo "   Using influx backup..."
        influx backup "$EXPORT_DIR/backup" \
            --token "${OLD_TOKEN}" \
            --host "${OLD_HOST}" 2>&1 || echo "   Backup method also failed"
    fi
fi

echo ""
echo "=== Migration Summary ==="
echo "Export location: $EXPORT_DIR/"
echo ""
echo "If automatic import fails, the data is preserved and can be imported later."

