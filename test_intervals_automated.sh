#!/bin/bash
# Automated polling interval testing
# Tests intervals from slowest to fastest, logs results

cd "$(dirname "$0")"

# Test intervals (in seconds) - test from current to fastest
INTERVALS=(30 20 15 10 5)

# Test duration per interval (seconds)
TEST_DURATION=180  # 3 minutes

# Results file
RESULTS_FILE="polling_test_results_$(date +%Y%m%d_%H%M%S).txt"

echo "🧪 Automated Polling Interval Test"
echo "===================================="
echo "Testing intervals: ${INTERVALS[*]} seconds"
echo "Duration per test: ${TEST_DURATION}s (3 minutes)"
echo "Results will be saved to: $RESULTS_FILE"
echo ""

# Initialize results file
{
    echo "Polling Interval Test Results"
    echo "Test started: $(date)"
    echo "Intervals tested: ${INTERVALS[*]}"
    echo "Test duration per interval: ${TEST_DURATION}s"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
} > "$RESULTS_FILE"

for interval in "${INTERVALS[@]}"; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Testing interval: ${interval}s"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Update interval in .env
    sed -i.bak "s/^POLL_INTERVAL=.*/POLL_INTERVAL=${interval}/" .env
    
    # Restart collector
    echo "⏳ Restarting collector..."
    docker-compose restart collector
    sleep 8  # Wait for collector to fully start
    
    # Clear previous logs for this test
    docker-compose logs --tail=0 collector > /dev/null 2>&1 || true
    
    echo "📊 Monitoring for ${TEST_DURATION} seconds..."
    
    # Monitor and collect stats
    START_TIME=$(date +%s)
    END_TIME=$((START_TIME + TEST_DURATION))
    
    ERROR_COUNT=0
    RATE_LIMIT_COUNT=0
    SUCCESS_COUNT=0
    DEVICE_COUNT=0
    
    # Monitor in intervals
    while [ $(date +%s) -lt $END_TIME ]; do
        sleep 10  # Check every 10 seconds
        
        # Get recent logs
        RECENT_LOGS=$(docker-compose logs --since 15s collector 2>&1)
        
        # Count events
        NEW_ERRORS=$(echo "$RECENT_LOGS" | grep -iE "(error|failed|exception)" | grep -v "INFO" | wc -l | tr -d ' ')
        NEW_RATE_LIMITS=$(echo "$RECENT_LOGS" | grep -iE "(rate limit|429|too many)" | wc -l | tr -d ' ')
        NEW_SUCCESS=$(echo "$RECENT_LOGS" | grep -E "Collected.*W from" | wc -l | tr -d ' ')
        DEVICE_INFO=$(echo "$RECENT_LOGS" | grep -E "Found.*online P110 devices" | tail -1)
        
        ERROR_COUNT=$((ERROR_COUNT + NEW_ERRORS))
        RATE_LIMIT_COUNT=$((RATE_LIMIT_COUNT + NEW_RATE_LIMITS))
        SUCCESS_COUNT=$((SUCCESS_COUNT + NEW_SUCCESS))
        
        if [ ! -z "$DEVICE_INFO" ]; then
            DEVICE_COUNT=$(echo "$DEVICE_INFO" | grep -oE "[0-9]+" | head -1)
        fi
        
        # Show progress
        ELAPSED=$(( $(date +%s) - START_TIME ))
        REMAINING=$(( END_TIME - $(date +%s) ))
        echo -ne "\r   Elapsed: ${ELAPSED}s / ${TEST_DURATION}s | Errors: ${ERROR_COUNT} | Rate Limits: ${RATE_LIMIT_COUNT} | Collections: ${SUCCESS_COUNT}"
        
        # Stop early if rate limiting detected
        if [ "$RATE_LIMIT_COUNT" -gt 0 ]; then
            echo ""
            echo "⚠️  Rate limiting detected! Stopping test early."
            break
        fi
    done
    
    echo ""  # New line after progress
    
    # Get final statistics
    ALL_LOGS=$(docker-compose logs collector 2>&1 | tail -200)
    FINAL_ERRORS=$(echo "$ALL_LOGS" | grep -iE "(error|failed|exception)" | grep -v "INFO" | wc -l | tr -d ' ')
    FINAL_RATE_LIMITS=$(echo "$ALL_LOGS" | grep -iE "(rate limit|429|too many)" | wc -l | tr -d ' ')
    FINAL_SUCCESS=$(echo "$ALL_LOGS" | grep -E "Collected.*W from" | wc -l | tr -d ' ')
    
    # Calculate metrics
    EXPECTED_POLLS=$((TEST_DURATION / interval))
    ACTUAL_POLLS=$FINAL_SUCCESS
    SUCCESS_RATE=$(echo "scale=1; ($ACTUAL_POLLS * 100) / ($EXPECTED_POLLS * ${DEVICE_COUNT:-34})" | bc 2>/dev/null || echo "0")
    
    # Determine status
    if [ "$FINAL_RATE_LIMITS" -gt 0 ]; then
        STATUS="❌ RATE LIMITED"
    elif [ "$FINAL_ERRORS" -gt 10 ]; then
        STATUS="⚠️  HIGH ERRORS"
    elif [ "$SUCCESS_RATE" -lt 80 ] 2>/dev/null; then
        STATUS="⚠️  LOW SUCCESS RATE"
    else
        STATUS="✅ OK"
    fi
    
    # Log results
    {
        echo "Interval: ${interval}s"
        echo "Status: $STATUS"
        echo "  - Test Duration: ${TEST_DURATION}s"
        echo "  - Devices: ${DEVICE_COUNT:-34}"
        echo "  - Expected Polls: ${EXPECTED_POLLS}"
        echo "  - Actual Collections: ${ACTUAL_POLLS}"
        echo "  - Errors: ${FINAL_ERRORS}"
        echo "  - Rate Limits: ${FINAL_RATE_LIMITS}"
        echo "  - Success Rate: ${SUCCESS_RATE}%"
        echo ""
    } | tee -a "$RESULTS_FILE"
    
    echo ""
    echo "Result: $STATUS"
    echo ""
    
    # Stop if rate limited
    if [ "$FINAL_RATE_LIMITS" -gt 0 ]; then
        echo "⛔ Rate limiting detected. Stopping tests."
        echo "   Safe interval appears to be: $((interval + 5))s or higher"
        break
    fi
    
    # Brief pause between tests
    if [ "$interval" != "${INTERVALS[-1]}" ]; then
        echo "⏸️  Pausing 10 seconds before next test..."
        sleep 10
    fi
done

# Restore to 30s default
echo ""
echo "🔄 Restoring default interval (30s)..."
sed -i.bak "s/^POLL_INTERVAL=.*/POLL_INTERVAL=30/" .env
docker-compose restart collector

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Testing Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📄 Full results saved to: $RESULTS_FILE"
echo ""
echo "Summary:"
cat "$RESULTS_FILE" | grep -E "(Interval:|Status:)" | tail -20

