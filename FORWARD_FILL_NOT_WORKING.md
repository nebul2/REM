# Forward-Fill Not Working - Root Cause

## Problem

The frontend forward-fill logic exists but isn't preventing the drops to 0W. Looking at the chart, totals still drop dramatically.

## Possible Issues

1. **Backend time bucket generation** - The code exists (line 307-336) but might not be working correctly
2. **Timestamp matching** - Backend-generated timestamps might not match TimescaleDB's actual bucket timestamps
3. **Forward-fill logic** - The JavaScript forward-fill might have a bug
4. **Changes not deployed** - The fixes might not be on pi400 yet

## Immediate Action

The best approach is to use the **database backfill script** to permanently fix historical data, OR check if the changes are actually deployed and working.

Let me verify the backend time bucket generation is working correctly first, then we can decide the best fix.

