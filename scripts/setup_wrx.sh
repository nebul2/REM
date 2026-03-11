#!/bin/bash
# Setup script for WRX migration - run this on WRX
# Sets up stats with NAS storage at /home/pi/nas/gos_stats

set -e

NAS_DATA_PATH="/home/pi/nas/gos_stats"
STATS_DIR="$HOME/stats"

echo "=== Stats WRX Setup Script ==="
echo "NAS path: $NAS_DATA_PATH"
echo "Stats directory: $STATS_DIR"
echo ""

# Step 1: Verify NAS directory exists
echo "Step 1: Verifying NAS directory..."
if [ ! -d "$NAS_DATA_PATH" ]; then
    echo "ERROR: NAS directory does not exist: $NAS_DATA_PATH"
    echo "Please create it first: mkdir -p $NAS_DATA_PATH"
    exit 1
fi
echo "✅ NAS directory exists"

# Step 2: Check if stats repo exists
echo ""
echo "Step 2: Checking stats repository..."
if [ ! -d "$STATS_DIR" ]; then
    echo "ERROR: Stats directory not found: $STATS_DIR"
    echo "Please clone the repo first:"
    echo "  cd ~ && git clone <repo-url> stats"
    exit 1
fi
echo "✅ Stats directory exists"

cd "$STATS_DIR"

# Step 3: Create .env file if it doesn't exist
echo ""
echo "Step 3: Setting up .env file..."
if [ ! -f ".env" ]; then
    if [ -f "ENV_TEMPLATE" ]; then
        cp ENV_TEMPLATE .env
        echo "✅ Created .env from template"
    else
        echo "ERROR: ENV_TEMPLATE not found"
        exit 1
    fi
else
    echo "✅ .env already exists"
fi

# Update NAS_DATA_PATH in .env
if ! grep -q "^NAS_DATA_PATH=" .env; then
    echo "" >> .env
    echo "# NAS Storage Path" >> .env
    echo "NAS_DATA_PATH=$NAS_DATA_PATH" >> .env
    echo "✅ Added NAS_DATA_PATH to .env"
else
    sed -i "s|^NAS_DATA_PATH=.*|NAS_DATA_PATH=$NAS_DATA_PATH|" .env
    echo "✅ Updated NAS_DATA_PATH in .env"
fi

# Step 4: Update docker-compose.yml to use NAS version
echo ""
echo "Step 4: Updating docker-compose.yml..."
if [ -f "docker-compose.nas.yml" ]; then
    cp docker-compose.yml docker-compose.yml.old 2>/dev/null || true
    cp docker-compose.nas.yml docker-compose.yml
    echo "✅ Updated docker-compose.yml to use NAS storage"
else
    echo "⚠️  docker-compose.nas.yml not found, you'll need to update docker-compose.yml manually"
fi

# Step 5: Create NAS directories
echo ""
echo "Step 5: Creating NAS data directories..."
mkdir -p "$NAS_DATA_PATH"/{timescaledb,admin,collector}
chmod -R 755 "$NAS_DATA_PATH"
echo "✅ NAS directories created:"
ls -la "$NAS_DATA_PATH"

# Step 6: Check Docker
echo ""
echo "Step 6: Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker not installed"
    exit 1
fi
if ! docker compose version &> /dev/null; then
    echo "ERROR: Docker Compose not available"
    exit 1
fi
echo "✅ Docker is available"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Make sure you have exported the database backup from Pi400"
echo "2. Copy the backup archive to WRX:"
echo "   scp /tmp/stats_migration_*.tar.gz d2@wrx:/tmp/"
echo ""
echo "3. Run the restore script:"
echo "   cd $STATS_DIR"
echo "   export NAS_DATA_PATH=$NAS_DATA_PATH"
echo "   ./scripts/restore_on_wrx.sh /tmp/stats_migration_*.tar.gz"
echo ""
echo "4. Start services:"
echo "   docker compose up -d"
echo ""
echo "5. Verify:"
echo "   docker compose ps"
echo "   curl http://localhost:7001/api/devices"



