# Fix Active Devices Panel - Alternative Methods

## Problem
Can't click the three dots menu on Active Devices panel to edit/remove it.

## Solutions

### Method 1: Click Panel Title Directly
1. **Click directly on the panel title** "Active Devices" (not the dots)
2. This should open the edit menu
3. Or try clicking anywhere on the panel itself

### Method 2: Use Dashboard Settings
1. Click **⚙️ Settings** (gear icon, top right)
2. Go to **"Panels"** or **"JSON Model"** tab
3. Find the Active Devices panel (id: 2)
4. You can edit or delete it from there

### Method 3: Delete via JSON
1. Click **⚙️ Settings** → **"JSON Model"** tab
2. Search for `"id": 2` or `"title": "Active Devices"`
3. Delete that entire panel object
4. Click **"Save changes"**

### Method 4: Keyboard Shortcut
1. Click on the Active Devices panel to select it
2. Press **Delete** key or **Backspace**
3. Confirm deletion

### Method 5: Right-Click Menu
1. **Right-click** anywhere on the Active Devices panel
2. Select **"Edit"** or **"Remove"** from context menu

### Method 6: Hide It Temporarily
If you can't delete it:
1. Edit dashboard (click ⚙️ Settings)
2. In panel grid, you can resize it to 0x0 or move it off screen
3. Or reduce its size to minimal

### Method 7: Simplest - Just Recreate Dashboard
1. Create a new dashboard
2. Copy panels you want to keep
3. Don't add the Active Devices panel
4. Delete the old dashboard

---

## Quick Fix: Edit Panel Query Instead

If you can access the panel at all:
1. Try **double-clicking** the panel
2. Or click the **small edit icon** (pencil) that might appear on hover
3. Fix the query to return just a number

**Better Query for Active Devices:**
```flux
from(bucket: "rem")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "gos_rem")
  |> group(columns: ["alias"])
  |> distinct(column: "alias")
  |> count()
```

Then in panel options, set to show only the value.

---

**If none of these work**, I can help you remove it via the dashboard JSON file directly.

