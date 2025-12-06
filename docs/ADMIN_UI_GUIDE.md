# Admin UI - Simple Device Group Manager

## What This Is

A simple web interface with **checkboxes** that lets non-technical users create device groups for experiments.

**No queries to write. No technical knowledge needed. Just checkboxes and names.**

---

## Access

Open in browser: **http://localhost:7001**

---

## How to Use

### Create a New Group (3 Steps)

1. **Enter Group Name**
   - Type a name like: "Experiment 1 - Streaming Test"
   - Or: "Experiment 2 - Encoding Comparison"

2. **Check Devices**
   - See all available devices listed as checkboxes
   - Check the ones you want in this group
   - Use "Select All" or "Deselect All" buttons if needed

3. **Click "Create Group"**
   - Done! Your group is saved

### Edit an Existing Group

1. Find the group in the "Existing Groups" section
2. Click **"Edit"** button
3. Check/uncheck devices as needed
4. Click **"Update Group"**

### Delete a Group

1. Find the group
2. Click **"Delete"** button
3. Confirm deletion

---

## Features

✅ **Simple Checkboxes** - No dropdowns, no complex UI  
✅ **Auto Device List** - Automatically shows all devices from InfluxDB  
✅ **Named Groups** - Give groups meaningful names  
✅ **Edit & Delete** - Manage groups easily  
✅ **Non-Technical** - Anyone can use it

---

## Example

**Group Name**: "Experiment 1 - Streaming Test"  
**Selected Devices**:
- ☑ London-Office-PC
- ☑ NYC-Studio-1
- ☑ LA-Encoder-2

**Result**: You can now filter Grafana dashboard by this group name!

---

## Next Steps

Once groups are created, they can be used in Grafana:
- Grafana dashboard will show groups as filter options
- Select a group to see only those devices
- Compare different groups side-by-side

---

**Perfect for non-technical analysts who just want to group devices easily!**

