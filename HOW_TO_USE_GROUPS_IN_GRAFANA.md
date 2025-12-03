# How to Use Device Groups in Grafana

## Overview

After creating device groups in the Admin UI (http://localhost:7001), you can use them in Grafana dashboards to filter devices.

## Current Status

Right now, Grafana doesn't automatically know about the groups. Here are **two options**:

---

## Option 1: Manual Setup (Quick - 5 minutes)

### Step 1: Create a Group in Admin UI
1. Go to http://localhost:7001
2. Create a group with checkboxes (e.g., "Experiment 1")
3. Note which devices are in the group

### Step 2: Use in Grafana
1. Open your Grafana dashboard
2. In the "Device Filter" dropdown, manually select the same devices
3. The graph will show only those devices

**Pros**: Works immediately, no setup needed  
**Cons**: You have to remember/select devices manually each time

---

## Option 2: Automatic Groups (Better - Requires Setup)

### Setup Steps

1. **Add HTTP API Datasource to Grafana**:
   - Grafana → Configuration → Data Sources
   - Add data source → "JSON API"
   - URL: `http://admin:7001`
   - Save

2. **Create Group Variable**:
   - Go to dashboard settings → Variables
   - Add variable:
     - Name: `device_group`
     - Type: `Query`
     - Data source: JSON API (the one you just added)
     - Query: `/api/groups/grafana`
     - Format: `JSON`

3. **Use in Panel Queries**:
   - Update your panel queries to use `$device_group` variable
   - It will filter devices based on selected group

**Pros**: Groups automatically appear, easy to switch  
**Cons**: Requires initial setup (10 minutes)

---

## Recommended: Option 3 - Simple Workaround

**Best for now**: Create groups in Admin UI, then manually select those devices in Grafana's existing device filter. Once you're comfortable, we can set up automatic integration.

**To filter by group in Grafana:**
1. Look at your group in Admin UI (see which devices are checked)
2. Open Grafana dashboard
3. Click "Device Filter" dropdown
4. Select the same devices from your group
5. Graph updates automatically

---

## Future Enhancement

We can add:
- Automatic group sync to Grafana
- Groups appearing as preset filters
- One-click group selection

For now, the manual method works fine for creating and using groups!

---

**Quick Answer**: Groups are created in Admin UI. To use them in Grafana, just manually select the same devices in Grafana's device filter dropdown. We can automate this later if needed.

