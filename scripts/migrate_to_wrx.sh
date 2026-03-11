#!/bin/bash
# Stats Migration Script: Pi400 → WRX with NAS Storage
# This script helps export data from Pi400 for migration

set -e

BACKUP_DIR="/tmp/stats_migration_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "=== Stats Migration Export Script ==="
echo "Backup directory: $BACKUP_DIR"
echo ""

# Check if running on Pi400
if ! docker ps | grep -q stats-timescaledb; then
    echo "ERROR: Stats containers not running. Please start them first."
    exit 1
fi

echo "Step 1: Exporting database..."
docker exec stats-timescaledb pg_dump -U gos -d gos_rem -Fc > "$BACKUP_DIR/database.dump"
if [ $? -eq 0 ]; then
    echo "✅ Database exported: $(du -h $BACKUP_DIR/database.dump | cut -f1)"
else
    echo "❌ Database export failed"
    exit 1
fi

echo ""
echo "Step 2: Exporting admin data..."
if [ -d "admin/data" ]; then
    tar -czf "$BACKUP_DIR/admin_data.tar.gz" \
        admin/data/device_groups.json \
        admin/data/experiments.json \
        admin/data/annotations.json \
        admin/data/snapshots.json \
        admin/data/snapshots/ 2>/dev/null || true
    echo "✅ Admin data exported"
else
    echo "⚠️  admin/data directory not found (may be in Docker volume)"
    # Try to copy from Docker volume
    if docker volume inspect stats_admin-data >/dev/null 2>&1; then
        VOLUME_PATH=$(docker volume inspect stats_admin-data | grep Mountpoint | cut -d'"' -f4)
        tar -czf "$BACKUP_DIR/admin_data.tar.gz" -C "$VOLUME_PATH" .
        echo "✅ Admin data exported from Docker volume"
    fi
fi

echo ""
echo "Step 3: Exporting collector token..."
if docker volume inspect stats_collector-data >/dev/null 2>&1; then
    VOLUME_PATH=$(docker volume inspect stats_collector-data | grep Mountpoint | cut -d'"' -f4)
    if [ -f "$VOLUME_PATH/refresh_token.txt" ]; then
        cp "$VOLUME_PATH/refresh_token.txt" "$BACKUP_DIR/"
        echo "✅ Collector token exported"
    else
        echo "⚠️  refresh_token.txt not found"
    fi
else
    echo "⚠️  Collector volume not found"
fi

echo ""
echo "Step 4: Creating manifest..."
cat > "$BACKUP_DIR/MANIFEST.txt" << EOF
Stats Migration Backup
Created: $(date)
Source: Pi400
Backup Contents:
- database.dump: PostgreSQL database dump (pg_dump format)
- admin_data.tar.gz: Admin UI data (groups, experiments, snapshots, annotations)
- refresh_token.txt: Collector refresh token

To restore on WRX:
1. Extract admin_data.tar.gz to NAS admin directory
2. Copy refresh_token.txt to NAS collector directory
3. Restore database.dump using pg_restore
EOF
echo "✅ Manifest created"

echo ""
echo "Step 5: Creating archive..."
cd "$(dirname "$BACKUP_DIR")"
ARCHIVE_NAME="stats_migration_$(date +%Y%m%d_%H%M%S).tar.gz"
tar -czf "$ARCHIVE_NAME" "$(basename "$BACKUP_DIR")"
echo "✅ Archive created: $ARCHIVE_NAME"
echo "   Size: $(du -h "$ARCHIVE_NAME" | cut -f1)"

echo ""
echo "=== Export Complete ==="
echo "Archive location: $ARCHIVE_NAME"
echo ""
echo "Next steps:"
echo "1. Transfer $ARCHIVE_NAME to WRX:"
echo "   scp $ARCHIVE_NAME d2@wrx:/tmp/"
echo ""
echo "2. On WRX, extract and follow migration guide:"
echo "   cd /tmp && tar -xzf $ARCHIVE_NAME"
echo "   See docs/MIGRATION_TO_WRX.md for full instructions"



