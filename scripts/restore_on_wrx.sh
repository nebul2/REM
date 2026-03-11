#!/bin/bash
# Stats Migration Restore Script for WRX
# Restores exported data from Pi400 to WRX with NAS storage

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_archive.tar.gz>"
    echo "Example: $0 /tmp/stats_migration_20251223_120000.tar.gz"
    exit 1
fi

BACKUP_ARCHIVE="$1"
BACKUP_DIR="/tmp/stats_restore_$(date +%Y%m%d_%H%M%S)"

if [ ! -f "$BACKUP_ARCHIVE" ]; then
    echo "ERROR: Backup archive not found: $BACKUP_ARCHIVE"
    exit 1
fi

# Check NAS_DATA_PATH is set (default to the actual path)
if [ -z "$NAS_DATA_PATH" ]; then
    NAS_DATA_PATH="/home/pi/nas/gos_stats"
    echo "Using default NAS_DATA_PATH: $NAS_DATA_PATH"
fi

if [ ! -d "$NAS_DATA_PATH" ]; then
    echo "ERROR: NAS path does not exist: $NAS_DATA_PATH"
    echo "Please mount NAS first or check the path"
    exit 1
fi

echo "=== Stats Migration Restore Script ==="
echo "Backup archive: $BACKUP_ARCHIVE"
echo "NAS data path: $NAS_DATA_PATH"
echo "Restore directory: $BACKUP_DIR"
echo ""

# Extract backup
echo "Step 1: Extracting backup archive..."
mkdir -p "$BACKUP_DIR"
tar -xzf "$BACKUP_ARCHIVE" -C "$BACKUP_DIR" --strip-components=1
echo "✅ Archive extracted"

# Verify backup contents
if [ ! -f "$BACKUP_DIR/database.dump" ]; then
    echo "ERROR: database.dump not found in backup"
    exit 1
fi

echo ""
echo "Step 2: Creating NAS directories..."
mkdir -p "$NAS_DATA_PATH"/{timescaledb,admin,collector}
echo "✅ Directories created"

echo ""
echo "Step 3: Restoring admin data..."
if [ -f "$BACKUP_DIR/admin_data.tar.gz" ]; then
    tar -xzf "$BACKUP_DIR/admin_data.tar.gz" -C "$NAS_DATA_PATH/admin"
    echo "✅ Admin data restored"
else
    echo "⚠️  admin_data.tar.gz not found, skipping"
fi

echo ""
echo "Step 4: Restoring collector token..."
if [ -f "$BACKUP_DIR/refresh_token.txt" ]; then
    cp "$BACKUP_DIR/refresh_token.txt" "$NAS_DATA_PATH/collector/"
    chmod 600 "$NAS_DATA_PATH/collector/refresh_token.txt"
    echo "✅ Collector token restored"
else
    echo "⚠️  refresh_token.txt not found, you'll need to get a new token"
fi

echo ""
echo "Step 5: Starting TimescaleDB (empty)..."
cd "$(dirname "$0")/.."
docker compose up -d timescaledb

# Wait for TimescaleDB to be healthy
echo "Waiting for TimescaleDB to be ready..."
for i in {1..60}; do
    if docker compose ps timescaledb | grep -q "healthy"; then
        echo "✅ TimescaleDB is ready"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "ERROR: TimescaleDB did not become healthy in time"
        exit 1
    fi
    sleep 2
done

echo ""
echo "Step 6: Restoring database..."
docker cp "$BACKUP_DIR/database.dump" stats-timescaledb:/tmp/database.dump

# Drop existing database if it exists and recreate
echo "Recreating database..."
docker exec stats-timescaledb psql -U gos -d postgres -c "DROP DATABASE IF EXISTS gos_rem;" || true
docker exec stats-timescaledb psql -U gos -d postgres -c "CREATE DATABASE gos_rem;"

# Restore database
echo "Restoring database dump (this may take a few minutes)..."
docker exec stats-timescaledb pg_restore -U gos -d gos_rem -v /tmp/database.dump

# Verify restore
ROW_COUNT=$(docker exec stats-timescaledb psql -U gos -d gos_rem -t -c "SELECT COUNT(*) FROM gos_rem;")
echo "✅ Database restored: $ROW_COUNT rows"

echo ""
echo "Step 7: Setting permissions..."
chown -R $USER:$USER "$NAS_DATA_PATH" 2>/dev/null || sudo chown -R $USER:$USER "$NAS_DATA_PATH"
chmod -R 755 "$NAS_DATA_PATH"
echo "✅ Permissions set"

echo ""
echo "=== Restore Complete ==="
echo ""
echo "Next steps:"
echo "1. Verify data:"
echo "   docker exec stats-timescaledb psql -U gos -d gos_rem -c 'SELECT COUNT(*), MAX(time) FROM gos_rem;'"
echo ""
echo "2. Start all services:"
echo "   docker compose up -d"
echo ""
echo "3. Check service status:"
echo "   docker compose ps"
echo ""
echo "4. Verify admin UI:"
echo "   curl http://localhost:7001/api/devices"
echo ""
echo "5. Clean up restore directory:"
echo "   rm -rf $BACKUP_DIR"

