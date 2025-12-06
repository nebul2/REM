# Pi400 Docker Platform Limitation

## Issue

Docker on Pi400 detects platform as `linux/arm/v8` (32-bit) but InfluxDB Docker image requires `linux/arm64/v8` (64-bit).

**However**: Native InfluxDB 2.7.5 (ARM64) runs perfectly on the same Pi400 hardware.

## Root Cause

Docker daemon appears to be running in 32-bit ARM mode even though:
- Hardware is ARM64 (aarch64)
- Native InfluxDB is ARM64 and working
- System architecture is aarch64

## Solutions

### Option A: Use Native InfluxDB (Current Workaround) ✅

The system currently uses native InfluxDB which works perfectly:
- ✅ Fully functional
- ✅ ARM64 performance
- ❌ Not portable (requires native install)

### Option B: Fix Docker Platform Detection

Try to configure Docker to use ARM64 mode:
```bash
# Check Docker architecture
docker info | grep Architecture

# May need to reinstall Docker in ARM64 mode
# Or configure Docker to use ARM64 emulation
```

### Option C: Use Alternative Database

TimescaleDB or PostgreSQL-based solution:
- ✅ Works reliably on all platforms
- ✅ No platform detection issues
- ⚠️ Requires code migration

### Option D: Document Limitation

For Pi400 specifically, use native InfluxDB. For other Docker environments (x86_64, ARM64 cloud), Docker InfluxDB works fine.

## Recommendation

Since the goal is portability:
1. **For Pi400**: Continue using native InfluxDB (works perfectly)
2. **For new deployments**: Docker InfluxDB will work on standard platforms
3. **Document**: This is a Pi400-specific Docker configuration issue

OR migrate to TimescaleDB which doesn't have this platform detection issue.

