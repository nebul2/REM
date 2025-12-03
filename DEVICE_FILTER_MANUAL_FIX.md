# Manual Fix for Device Filter Dropdown

If the device filter still doesn't show devices after re-import, fix it manually in Grafana:

## Steps

1. **Go to Dashboard Settings**
   - Click ⚙️ Settings (gear icon, top right)
   - Click "Variables" tab

2. **Edit device_filter Variable**
   - Find "device_filter" in the list
   - Click "Edit"

3. **Update Query Settings**

   **Query:**
   ```flux
   import "influxdata/influxdb/schema"
   
   schema.measurementTagValues(
     bucket: "rem",
     measurement: "gos_rem",
     tag: "alias"
   )
   ```

   **OR try this simpler version:**
   ```flux
   from(bucket: "rem")
     |> range(start: -24h)
     |> filter(fn: (r) => r._measurement == "gos_rem")
     |> group(columns: ["alias"])
     |> distinct(column: "alias")
     |> sort()
   ```

4. **Check These Settings:**
   - **Data source:** InfluxDB
   - **Refresh:** On Dashboard Load (or On Time Range Change)
   - **Multi-value:** ✅ ON
   - **Include All option:** ✅ ON
   - **Format:** Leave as default or try "Text"

5. **Test the Query**
   - Click "Test query" button (if available)
   - Should show list of device names
   - If it shows data, click "Apply"

6. **If Still Not Working**

   Try changing the **Format** option:
   - Try: "Text"
   - Try: "Single quote"
   - Try: "Double quote"

   OR change **Refresh** to:
   - "On Time Range Change"
   - "On Dashboard Load"
   - "Manual"

7. **Save**
   - Click "Apply"
   - Click "Save dashboard"

---

**Alternative:** If variable still doesn't work, you can filter devices directly in panel queries by editing them manually in each panel.

