# Fix Panel Query Errors

## Error
```
Status: 500. Message: invalid: error @5:114-5:119: undefined identifier Arian
error @5:120-5:123: undefined identifier STB
error @5:114-5:123: invalid binary operator <INVALID_OP>
```

## Cause
Device names with spaces (like "Arian STB") are being treated as identifiers instead of strings in the Flux queries. The variable filter syntax is wrong.

## Fix: Update Panel Queries

You need to fix the filter syntax in each panel query. Here's how:

### Step 1: Edit Each Panel

For each panel that uses `device_filter`:

1. Click panel title → **Edit**
2. Go to the query editor
3. Find the filter line that looks like:
```flux
|> filter(fn: (r) => contains(value: r.alias, set: ${device_filter:json}))
```

### Step 2: Replace with Correct Syntax

Replace that filter with one of these:

**Option A - Using regex (Recommended for multi-select):**
```flux
|> filter(fn: (r) => r["alias"] =~ /${device_filter:regex}/)
```

**Option B - Using contains with proper handling:**
```flux
|> filter(fn: (r) => if "${device_filter:csv}" == "" then true else contains(value: r.alias, set: ${device_filter:csv}))
```

**Option C - Simple regex match (works best):**
```flux
|> filter(fn: (r) => r.alias =~ /${device_filter:regex}/)
```

### Step 3: For All Panels

Update these panels:
1. **Power Consumption by Device** (timeseries graph)
2. **Top Power Consumers** (bargauge)
3. **Current Power by Device** (table)

### Quick Fix Query Template

Here's a working query template for panels:

```flux
from(bucket: "rem")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "gos_rem")
  |> filter(fn: (r) => r._field == "powerWatts")
  |> filter(fn: (r) => r["alias"] =~ /${device_filter:regex}/)
  |> aggregateWindow(every: ${interval:raw}, fn: mean, createEmpty: false)
  |> yield(name: "mean")
```

## Alternative: Fix Variable Format

If you want to keep using `contains()`, change the variable format:

1. Edit `device_filter` variable
2. In **Selection Options**, set:
   - **Format:** `Single quote, CSV`
   - Or **Format:** `Double quote, CSV`

Then use in queries:
```flux
|> filter(fn: (r) => contains(value: r.alias, set: ${device_filter:csv}))
```

---

**Recommended:** Use the regex format (`=~ /${device_filter:regex}/`) as it handles spaces and special characters automatically.

