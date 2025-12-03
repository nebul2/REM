#!/bin/bash
# Test different polling intervals to find optimal rate
# This script changes the interval, restarts the collector, and monitors for errors

INTERVAL=$1

if [ -z "$INTERVAL" ]; then
    echo "Usage: ./test_polling_rate.sh <interval_in_seconds>"
    echo "Example: ./test_polling_rate.sh 10"
    echo ""
    echo "Suggested intervals to test: 30, 20, 15, 10, 5"
    exit 1
fi

cd "$(dirname "$0")"

echo "🧪 Testing polling interval: ${INTERVAL} seconds"
echo ""

# Check if collector is running
if ! docker-compose ps collector | grep -q "Up"; then
    echo "❌ Collector is not running. Start it first with: docker-compose up -d"
    exit 1
fi

# Update POLL_INTERVAL in .env
echo "📝 Updating POLL_INTERVAL to ${INTERVAL}s..."
if grep -q "^POLL_INTERVAL=" .env; then
    sed -i.bak "s/^POLL_INTERVAL=.*/POLL_INTERVAL=${INTERVAL}/" .env
else
    echo "POLL_INTERVAL=${INTERVAL}" >> .env
fi

# Restart collector
echo "🔄 Restarting collector..."
docker-compose up -d collector

# Wait for it to start
echo "⏳ Waiting 5 seconds for collector to start..."
sleep 5

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Monitoring collector logs..."
echo "Watch for errors, rate limits, or API failures"
echo "Press Ctrl+C to stop monitoring"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Show live logs with error highlighting
docker-compose logs -f collector 2>&1 | \
    while IFS= read -r line; do
        if echo "$line" | grep -qiE "(error|failed|exception|timeout|rate limit|429|503)"; then
            echo "❌ ERROR: $line" 
        elif echo "$line" | grep -qiE "(collected|found.*devices)"; then
            echo "✅ $line"
        else
            echo "$line"
        fi
    done

