# Simple Answer: How to Use Groups in Grafana

## You Already Have a Group!

I can see you created: **"REM Test Group 1"** with 13 devices.

---

## How to Use It in Grafana (Right Now)

### Current Method: Manual Selection

1. **Open Grafana**: http://localhost:7003
2. **Find the "Device Filter" dropdown** at the top of your dashboard
3. **Select the same devices** that are in your group:
   - BHL USA_Asus display -27
   - Ben HD LCD monitor (Pi)
   - Ben Raspberry Pi
   - DR001-id3as
   - DR002-WRX
   - DR003-TV-65-LED-(Roku)
   - Kit P110
   - STJ BT Hub
   - STJ Datça 1
   - STJ Datça 2
   - STJ LG Monitor
   - STJ Prototype 8K
   - Stan-42"Plasma

4. **Dashboard updates** to show only those devices!

---

## Why Manual?

Grafana doesn't automatically read from the Admin UI yet. The groups are stored but need to be manually selected.

**Think of it this way:**
- **Admin UI** = Your "recipe book" (reminds you which devices)
- **Grafana** = Your "cooking" (you recreate the selection)

---

## Want Automatic Groups?

I can set it up so groups appear as dropdown options in Grafana. Then you'd just:
- Click "REM Test Group 1" in Grafana
- Dashboard automatically filters to those 13 devices

**Want me to set this up?** It takes about 10 minutes to configure.

---

## Quick Summary

**What works now:**
✅ Create groups in Admin UI (checkboxes - super easy!)
✅ Use groups by manually selecting same devices in Grafana
✅ Groups are your "cheat sheet" for which devices to pick

**What we can add:**
⏳ Groups appear as dropdown in Grafana (automatic filtering)

---

**Bottom line:** Your group is ready! Just manually select those 13 devices in Grafana's device filter dropdown. We can automate it later if you want one-click filtering!

