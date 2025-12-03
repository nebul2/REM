#!/bin/bash
# Test different polling intervals to find maximum rate
# Monitors for errors, rate limiting, and API failures

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Test intervals in seconds (from slowest to fastest)
INTERVALS=(30 20 15 10 5 3 2 1)

# Duration to test each interval (in seconds)
TEST_DURATION=120  # 2 minutes per interval

# Log file
LOG_FILE="polling_test_results.log"

echo "================================================" > "$LOG_FILE"
echo "Polling Interval Test Results" >> "$LOG_FILE"
echo "Started: $(date)" >> "$LOG_FILE"
echo "================================================" >> "$LOG_FILE"
echo ""

echo "🧪 Testing Polling Intervals"
echo "Will test: ${INTERVALS[*]} seconds"
echo "Duration per test: ${TEST_DURATION}s (2 minutes)"
echo "Results will be logged to: $LOG_FILE"
echo ""

# Check if docker-compose is running
if ! docker-compose ps | grep -q "stats-collector"; then
    echo "❌ Collector is not running. Start it first with: docker-compose up -d"
    exit 1
fi

for interval in "${INTERVALS[@]}"; do
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Testing interval: ${interval}s"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Update .env file
    if grep -q "^POLL_INTERVAL=" .env; then
        sed -i.bak "s/^POLL_INTERVAL=.*/POLL_INTERVAL=${interval}/" .env
    else
        echo "POLL_INTERVAL=${interval}" >> .env
    fi
    
    # Restart collector with new interval
    echo "⏳ Restarting collector with ${interval}s interval..."
    docker-compose up -d collector
    
    # Wait for collector to start
    sleep 5
    
    # Get initial log position
    INITIAL_LOG_LINES=$(docker-compose logs collector | wc -l)
    
    echo "📊 Monitoring for ${TEST_DURATION} seconds..."
    echo "   Watching for errors, rate limits, and API failures..."
    
    # Monitor for the test duration
    START_TIME=$(date +%s)
    END_TIME=$((START_TIME + TEST_DURATION))
    
    ERROR_COUNT=0
    SUCCESS_COUNT=0
    RATE_LIMIT_COUNT=0
    
    while [ $(date +%s) -lt $END_TIME ]; do
        # Check logs for errors
        CURRENT_LOGS=$(docker-compose logs --since 5s collector 2>&1)
        
        # Count errors
        NEW_ERRORS=$(echo "$CURRENT_LOGS" | grep -iE "(error|failed|exception|timeout|rate limit|429|503)" | wc -l | tr -d ' ')
        NEW_RATE_LIMITS=$(echo "$CURRENT_LOGS" | grep -iE "(rate limit|429|too many)" | wc -l | tr -d ' ')
        NEW_SUCCESS=$(echo "$CURRENT_LOGS" | grep -E "Collected.*W from" | wc -l | tr -d ' ')
        
        ERROR_COUNT=$((ERROR_COUNT + NEW_ERRORS))
        RATE_LIMIT_COUNT=$((RATE_LIMIT_COUNT + NEW_RATE_LIMITS))
        SUCCESS_COUNT=$((SUCCESS_COUNT + NEW_SUCCESS))
        
        # If we see rate limiting, stop early
        if [ "$RATE_LIMIT_COUNT" -gt 0 ]; then
            echo "⚠️  Rate limiting detected! Stopping test early."
            break
        fi
        
        sleep 5
    done
    
    # Get final statistics
    TOTAL_LOGS=$(docker-compose logs collector | tail -100)
    DEVICE_COUNT=$(echo "$TOTAL_LOGS" | grep -E "Found.*online P110 devices" | tail -1 | grep -oE "[0-9]+" | head -1 || echo "0")
    
    # Calculate metrics
    EXPECTED_POLLS=$((TEST_DURATION / interval))
    SUCCESS_RATE=$(echo "scale=2; ($SUCCESS_COUNT / $EXPECTED_POLLS) * 100" | bc 2>/dev/null || echo "0")
    
    # Log results
    {
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Interval: ${interval}s"
        echo "Test Duration: ${TEST_DURATION}s"
        echo "Expected Polls: ${EXPECTED_POLLS}"
        echo "Successful Collections: ${SUCCESS_COUNT}"
        echo "Errors: ${ERROR_COUNT}"
        echo "Rate Limits: ${RATE_LIMIT_COUNT}"
        echo "Devices Found: ${DEVICE_COUNT}"
        echo "Success Rate: ${SUCCESS_RATE}%"
        echo "Status: $([ "$RATE_LIMIT_COUNT" -gt 0 ] && echo '❌ RATE LIMITED' || [ "$ERROR_COUNT" -gt 5 ] && echo '⚠️  HIGH ERRORS' || echo '✅ OK')"
        echo ""
    } | tee -a "$LOG_FILE"
    
    # Stop if we hit rate limits
    if [ "$RATE_LIMIT_COUNT" -gt 0 ]; then
        echo ""
        echo "⛔ Rate limiting detected at ${interval}s interval"
        echo "   Recommendation: Use at least $((interval + 5))s to be safe"
        break
    fi
    
    # Warn about high error rate
    if [ "$ERROR_COUNT" -gt 5 ]; then
        echo "⚠️  High error rate at ${interval}s interval"
        echo "   Consider using a slower interval"
    fi
    
    # Brief pause between tests
    if [ "$interval" != "${INTERVALS[-1]}" ]; then
        echo "⏸️  Pausing 10 seconds before next test..."
        sleep 10
    fi
done

# Restore to original interval (30s)
echo ""
echo "🔄 Restoring to default interval (30s)..."
sed -i.bak "s/^POLL_INTERVAL=.*/POLL_INTERVAL=30/" .env
docker-compose up -d collector

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Testing Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📄 Full results: $LOG_FILE"
echo ""
echo "Summary:"
grep -A 10 "Interval:" "$LOG_FILE" | grep -E "(Interval:|Status:)" | tail -20

