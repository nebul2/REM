# Simple Dashboard - What You Need

## New Simplified Dashboard: `GOS_REM_Dashboard_Simple.json`

### What It Has:
✅ **One clean graph** - Power Consumption by Device  
✅ **Shows all selected devices** - Each device as its own line  
✅ **Average line** - Red, thicker line showing average across all selected devices  
✅ **Aggregate line** - Red, thicker line showing total (sum) of all selected devices  
✅ **Device filter dropdown** - Multi-select devices  
✅ **Time interval selector** - Choose aggregation: 10s, 30s, 1m, 5m, 15m, 1h  
✅ **Time range picker** - Built into Grafana (top right): Last 15 mins, Last hour, Last 24h, etc.  
✅ **Y-axis scaling** - Variable to set fixed or auto scale (will be implemented)

### What's Removed:
❌ Total Power panel (not needed)  
❌ Top Power Consumers panel (not needed)  
❌ Multiple experiment dropdowns (too complex)

---

## How to Group Devices (Easy Method)

### Use Grafana Snapshots - Super Simple!

**For Non-Technical Users - Just 3 Steps:**

1. **Select Devices**
   - Click "Device Filter" dropdown
   - Select the devices you want (can select multiple)
   - Close dropdown

2. **Set Time Range** (if needed)
   - Click time picker (top right)
   - Choose "Last 15 minutes" or "Last 1 hour" or custom
   - Or leave as default

3. **Save as Snapshot**
   - Click **"Share"** button (top right of dashboard)
   - Click **"Snapshot"** tab
   - Enter name: "Experiment 1 - Streaming Test" (or whatever)
   - Click **"Local Snapshot"**
   - **Copy the URL** - this is your saved experiment group!

### To View Saved Experiment:
Just open the snapshot URL - it shows everything:
- Your selected devices
- Time range
- All settings

### To Create Another Experiment:
1. Select different devices
2. Set time range if needed  
3. Share → Snapshot → Name it "Experiment 2"
4. Done!

### Benefits:
- ✅ Super simple (3 clicks)
- ✅ No technical knowledge needed
- ✅ Unlimited experiments
- ✅ Easy to share (just send URL)
- ✅ Can compare by opening multiple snapshots

---

## How to Import

1. In Grafana, go to **Dashboards** → **New** → **Import**
2. Click **"Upload JSON file"**
3. Select `grafana/dashboards/GOS_REM_Dashboard_Simple.json`
4. Click **"Load"**
5. Click **"Import"**

Done! Now you can:
- Select devices
- See individual device lines + Average + Aggregate
- Set time range easily
- Create snapshots for experiments

---

## Next Steps

The dashboard is ready to use. For grouping devices, use Snapshots - it's the simplest solution for your non-technical users!

