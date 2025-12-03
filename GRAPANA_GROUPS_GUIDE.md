# How to Find Groups in Grafana Dashboard

## Current Situation

Groups are created in the **Admin UI** (http://localhost:7001), but Grafana doesn't automatically show them as dropdown options yet.

---

## How to Use Groups Right Now

### Step 1: Create Group in Admin UI
1. Go to **http://localhost:7001**
2. Create a device group:
   - Enter name: "Experiment 1 - Streaming Test"
   - Check the devices you want
   - Click "Create Group"

### Step 2: Use Group in Grafana

**Option A: Manual Selection** (Easiest - works now)
1. Open Grafana dashboard: **http://localhost:7003**
2. Look at the **"Device Filter"** dropdown at the top of the dashboard
3. Manually select the same devices you checked in your group
4. Dashboard updates immediately

**Option B: Remember the Devices** (Recommended)
1. View your group in Admin UI to see which devices are in it
2. In Grafana, select those same devices from the dropdown
3. Group acts as your "cheat sheet" for which devices to pick

---

## Why This Way?

Grafana variables need to come from data sources (like InfluxDB). To automatically show groups as dropdown options, we'd need to:
- Set up an HTTP datasource in Grafana
- Configure variables to query the Admin API
- Map groups to device filters

**This is possible but takes 10-15 minutes to set up.** For now, the manual method works perfectly!

---

## Future: Automatic Groups

We can make groups appear automatically in Grafana by:
1. Adding an HTTP datasource pointing to Admin UI
2. Creating a variable that queries `/api/groups`
3. Using that variable in panel queries

**Want me to set this up?** It's a one-time configuration that makes groups clickable in Grafana.

---

## Quick Summary

**Right now:**
- ✅ Create groups in Admin UI (checkboxes - super easy!)
- ✅ Use groups by manually selecting the same devices in Grafana
- ✅ Groups act as your "recipe" or checklist

**Later (if you want):**
- ⏳ Groups appear as dropdown options in Grafana
- ⏳ Click group name to filter automatically
- ⏳ No manual device selection needed

---

**Bottom line:** Groups are working! You just manually recreate the selection in Grafana's device filter. We can automate it later if you want.

