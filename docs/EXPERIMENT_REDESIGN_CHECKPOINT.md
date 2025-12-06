# Experiment Redesign - Checkpoint 1

## Tag: `experiment-redesign-part1`

This checkpoint marks the completion of the backend and structural frontend changes for the experiment/group separation redesign.

## What's Done

### Backend (`admin/app.py`)
- ✅ Experiments now have time ranges and link to groups (not devices directly)
- ✅ Added `is_current` flag to support ongoing experiments
- ✅ Added `/api/experiments/{id}/start` endpoint to mark experiment as current
- ✅ Added `/api/experiments/{id}/end` endpoint to end current experiment
- ✅ Updated experiment creation to support current vs past experiments
- ✅ End time is optional for current experiments (set when experiment ends)

### Frontend Structure (`admin/templates/exploration.html`)
- ✅ Renamed "Experiment A/B" to "Chart A/B" throughout UI
- ✅ Chart controls now have two dropdowns:
  - First: Select experiment
  - Second: Select groups from that experiment (populated dynamically)
- ✅ Added "Start Experiment" and "End Experiment" buttons to action buttons row
- ✅ Experiment creation modal supports "Current Experiment" checkbox
- ✅ End time field is optional when creating current experiments

### Frontend Logic (`admin/static/exploration.js`)
- ⏳ **TODO**: Update chart loading logic for new structure
- ⏳ **TODO**: Populate groups dropdown based on selected experiment
- ⏳ **TODO**: Auto-set chart time range to experiment's time range for past experiments
- ⏳ **TODO**: Handle current experiment time scoping (start time to "now")
- ⏳ **TODO**: Update experiment creation to send `is_current` flag

## To Restore to This Point

```bash
git checkout experiment-redesign-part1
```

Or if you want to create a branch from this point:

```bash
git checkout -b restore-from-checkpoint experiment-redesign-part1
```

## Next Steps

1. Update JavaScript to handle new chart structure
2. Implement dynamic group dropdown population
3. Add auto time-range setting for past experiments
4. Implement current experiment time scoping
5. Test the complete flow

## Experiment Structure

Experiments now have:
```json
{
  "id": "experiment-id",
  "name": "Experiment Name",
  "description": "...",
  "time_range": {
    "start": "2025-12-05T10:00:00Z",
    "end": "2025-12-05T12:00:00Z"  // Optional for current experiments
  },
  "is_current": false,
  "linked_groups": ["group-a", "group-b"],
  "created_at": "...",
  "updated_at": "..."
}
```

## Groups vs Experiments

- **Groups**: Collections of devices (participant groups)
- **Experiments**: Time-based studies that link to groups
  - Can be past (has start and end time)
  - Can be current (has start time, end time set when stopped)
