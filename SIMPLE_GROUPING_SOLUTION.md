# Simple Device Grouping Solution

## Problem
Need easy way for non-technical users to:
1. Select multiple devices
2. Save them as named groups/experiments
3. Compare different groups

## Solution: Use Grafana Dashboard Snapshots or Saved Filters

### Option 1: Dashboard Snapshots (Recommended)
Grafana has built-in "snapshots" feature that saves the entire dashboard state including variable selections.

**How to use:**
1. Select devices in "Device Filter" dropdown
2. Set time range (Last 15 mins, Last hour, etc.)
3. Click **"Share"** button (top right)
4. Click **"Snapshot"** tab
5. Name it: "Experiment 1 - Streaming Test" (or whatever)
6. Click **"Local Snapshot"**
7. Copy the URL - this is your saved experiment group!

**Benefits:**
- Super easy for non-technical users
- Saves device selection + time range + all settings
- Can share URLs with team
- Can create multiple snapshots for different experiments
- No technical knowledge needed

### Option 2: Multiple Dashboards
Create separate dashboards for each experiment:
- "Experiment 1" dashboard
- "Experiment 2" dashboard
- etc.

Each dashboard has device filter pre-configured.

**How to use:**
1. Duplicate dashboard
2. Rename to "Experiment 1"
3. Configure device filter for that experiment
4. Save

### Option 3: Grafana Annotations (For Timeline)
Use Grafana annotations to mark experiment periods:
- Add annotation: "Experiment 1 started"
- Shows on timeline
- Can filter devices per annotation

## Recommended: Use Snapshots

Snapshots are perfect for your use case:
- ✅ Super simple (just "Share → Snapshot")
- ✅ Saves everything (devices, time range, settings)
- ✅ Can create unlimited experiments
- ✅ Easy to share with team
- ✅ Non-technical users can do it

## New Simplified Dashboard

I've created `GOS_REM_Dashboard_Simple.json` with:
- ✅ One clean graph (Power Consumption by Device)
- ✅ Shows all selected devices
- ✅ Shows Average line (red, thicker)
- ✅ Shows Aggregate line (red, thicker)
- ✅ Device filter dropdown
- ✅ Aggregation interval selector
- ✅ Time range selector (Last 15 mins, Last hour, etc.)
- ✅ Y-axis can be fixed or auto (via variable)

**To use:**
1. Import `GOS_REM_Dashboard_Simple.json`
2. Select devices
3. Set time range
4. Create snapshot: Share → Snapshot → Name it "Experiment 1"
5. Repeat for other experiments

---

**For grouping:** Use Snapshots - it's the simplest solution for non-technical users!

