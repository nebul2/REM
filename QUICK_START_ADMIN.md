# Quick Start: Admin UI for Device Groups

## What This Solves

**Problem**: Non-technical analysts need to group devices but Grafana's interface is too complex.

**Solution**: Simple checkbox web UI - no queries, no technical knowledge needed!

---

## Start the Admin UI

```bash
# Start all services (including admin UI)
docker-compose up -d

# Access admin UI
open http://localhost:7001
```

---

## How to Use (Super Simple!)

### 1. Create a Device Group

1. Open http://localhost:7001 in browser
2. **Enter group name**: "Experiment 1 - Streaming Test"
3. **Check devices**: Click checkboxes for devices you want
4. **Click "Create Group"** - Done!

### 2. Use Groups in Grafana

Groups are automatically available in Grafana dashboard:
- Open Grafana dashboard
- Device filter dropdown shows your groups
- Select a group to see only those devices

---

## Example Workflow

**Analyst wants to create "Experiment 1":**

1. Goes to http://localhost:7001
2. Sees all devices as checkboxes:
   - ☐ London-Office-PC
   - ☐ NYC-Studio-1
   - ☐ LA-Encoder-2
   - ☐ Tokyo-Test-Server

3. Checks the ones needed:
   - ☑ London-Office-PC
   - ☑ NYC-Studio-1
   - ☑ LA-Encoder-2

4. Types name: "Experiment 1 - Streaming Test"
5. Clicks "Create Group"

**Result**: Group saved! Can now use in Grafana.

---

## Features

- ✅ Checkbox interface (no dropdowns)
- ✅ Auto-fetches devices from InfluxDB
- ✅ Edit groups anytime
- ✅ Delete groups you don't need
- ✅ Works for non-technical users

---

**That's it! Much simpler than teaching analysts to write queries.**

