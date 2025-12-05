#!/bin/bash
# Quick script to check for null/missing data patterns

echo "Checking collector error handling..."
echo "The collector should skip failed devices and log warnings."
echo ""
echo "To check logs on pi400, run:"
echo "  ssh d2@pi400 'docker logs stats-collector --tail 100 | grep -i \"failed\\|error\\|warning\"'"
echo ""
echo "The issue is likely:"
echo "  1. API calls failing intermittently (rate limiting?)"
echo "  2. Failed devices create gaps in time buckets"
echo "  3. Frontend treats missing devices as 0"
echo ""
echo "I'll implement forward-fill to use last known value for missing devices."
