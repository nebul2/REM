# Using Device Groups in Grafana Dashboard

## Quick Answer

**Groups you create in Admin UI are stored but not automatically visible in Grafana yet.**

Here's the **easiest way** to use them right now:

---

## Method 1: Manual Selection (Works Now)

1. **Create group in Admin UI**: http://localhost:7001
   - Name it (e.g., "Experiment 1")
   - Check devices
   - Save

2. **Use in Grafana**:
   - Open Grafana dashboard: http://localhost:7003
   - Look at the "Device Filter" dropdown at the top
   - Manually select the same devices you checked in the group
   - Dashboard updates to show only those devices

**That's it!** The group acts as a reminder of which devices to select.

---

## Method 2: See Groups Directly (Future Enhancement)

We're working on making groups appear automatically in Grafana. For now, the manual method works fine.

---

## Current Workflow

1. **Plan your experiment** → Think about which devices
2. **Create group in Admin UI** → Name it, check devices, save
3. **Open Grafana** → Select same devices from dropdown
4. **Analyze data** → See your experiment data

The group acts as your "recipe" - you just recreate it in Grafana's filter.

---

## Want Automatic Groups?

If you want groups to appear automatically in Grafana (so you can just click "Experiment 1" instead of selecting devices), let me know and we can set that up. It requires a bit more configuration but it's definitely doable!

---

**Bottom line**: Groups work as a "checklist" right now. Create the group to remember which devices, then manually select them in Grafana's filter.

