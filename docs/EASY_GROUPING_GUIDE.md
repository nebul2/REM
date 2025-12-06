# Easy Device Grouping for Non-Technical Users

## The Problem
Need easy way to:
- Select multiple devices
- Save them as named groups (e.g., "Experiment 1")
- Compare different experiments
- Simple enough for non-technical users

## Solution: Use Grafana Snapshots ✅

**Snapshots** save the entire dashboard state - including:
- Selected devices
- Time range
- All settings

### How to Create an Experiment Group (3 steps):

1. **Select Devices**
   - Click "Device Filter" dropdown
   - Select the devices you want (can select multiple)
   - Close dropdown

2. **Set Time Range** (optional)
   - Use time picker (top right)
   - Choose "Last 15 minutes", "Last 1 hour", etc.
   - Or set custom range

3. **Save as Snapshot**
   - Click **"Share"** button (top right)
   - Click **"Snapshot"** tab
   - Enter name: "Experiment 1 - Streaming Test" (or whatever you want)
   - Click **"Local Snapshot"**
   - Copy the URL - this is your saved experiment!

### To View Saved Experiment:

Just open the snapshot URL - it will show:
- Your selected devices
- The time range you set
- All the data

### To Create Another Experiment:

1. Select different devices
2. Set time range if needed
3. Share → Snapshot → Name it "Experiment 2"
4. Done!

### Benefits:

- ✅ Super simple (3 clicks)
- ✅ No technical knowledge needed
- ✅ Unlimited experiments
- ✅ Easy to share with team (just send URL)
- ✅ Can compare by opening multiple snapshot URLs
- ✅ Each snapshot remembers everything

---

## Alternative: Multiple Dashboards

If snapshots don't work for your workflow:

1. Duplicate dashboard
2. Rename to "Experiment 1"
3. Select devices for that experiment
4. Save

Repeat for each experiment.

---

**Recommendation:** Start with Snapshots - it's the easiest for non-technical users!

