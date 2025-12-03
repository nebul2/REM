# GOS REM Data Exploration UI - Project Plan

## Vision

Transform the admin UI into a comprehensive data exploration tool for GOS REM experiments. The collector remains as a "data logger" - this new UI reads from InfluxDB to explore and analyze streaming energy experiments.

---

## Architecture

```
┌─────────────────┐
│  Data Collector │  (Existing - unchanged)
│  (Data Logger)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    InfluxDB     │  (Time-series database)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│   GOS REM Exploration UI (NEW)      │
│   - Experiment Management           │
│   - Data Visualization              │
│   - Annotations                     │
│   - Snapshots/Gallery               │
└─────────────────────────────────────┘
```

---

## Core Features

### 1. Experiment/Group Management
- **Create experiment groups** (A, B, etc.) with device selection
- **Filter by experiment** - only show devices in selected group
- **Multi-experiment view** - compare A vs B side-by-side
- **Re-run experiments** - change group membership, re-analyze same time range

### 2. Data Visualization
- **Time-series charts** - Power consumption over time
- **Multiple devices** - All devices in experiment shown as lines
- **Statistical overlays** - Toggle mean, median, min, max
- **Aggregate lines** - Total and average across all devices

### 3. Energy Calculations
- **Total energy** - Sum of all devices over time range (kWh)
- **Average energy** - Mean across devices
- **Per-device totals** - Individual device energy consumption
- **Comparison** - Energy difference between experiments

### 4. Timeline Annotations
- **Add annotations** - Mark specific test points on timeline
- **Edit/delete** - Manage annotations
- **Colored markers** - Different colors for different test types
- **Description** - Notes about what was being tested

### 5. Snapshot & Archive
- **Save snapshots** - Capture current chart state
- **Add metadata** - Title, description, experiment name, annotations
- **Gallery view** - Browse all saved snapshots
- **Filter/search** - Find snapshots by experiment, date, etc.
- **Compare snapshots** - Side-by-side view of different experiments
- **Export** - Download snapshot as image/PDF

### 6. GoS Branding
- **Logo** - Use provided GoS logo
- **Color scheme** - Match logo colors (green theme)
- **Favicon** - GoS logo as favicon
- **Theming** - Consistent green/white styling

---

## Technology Stack

- **Backend**: FastAPI (already started)
- **Frontend**: Modern JavaScript (Chart.js or D3.js for visualization)
- **Database**: InfluxDB (already connected)
- **Storage**: JSON files for experiments/snapshots (or SQLite for more structure)

---

## UI Layout

### Main Dashboard
```
┌─────────────────────────────────────────────────────────┐
│  [GoS Logo]  GOS REM Data Exploration                   │
├─────────────────────────────────────────────────────────┤
│  Experiments: [Select A] [Select B] [Create New]       │
│  Time Range: [Last 1h ▼] [Custom Range]                │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐  ┌──────────────────────┐   │
│  │  Experiment A Chart  │  │  Experiment B Chart  │   │
│  │                      │  │                      │   │
│  │  [Chart]             │  │  [Chart]             │   │
│  │                      │  │                      │   │
│  └──────────────────────┘  └──────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  Stats: Total: X kWh | Avg: Y W | Mean: Z W           │
│  [📌 Add Annotation] [💾 Save Snapshot] [📊 Gallery]   │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Foundation
- [x] FastAPI backend structure
- [ ] Basic chart visualization
- [ ] Experiment group management
- [ ] InfluxDB data reading

### Phase 2: Core Features
- [ ] Statistical toggles (mean/median)
- [ ] Energy calculations
- [ ] Timeline annotations
- [ ] A/B comparison view

### Phase 3: Snapshots & Archive
- [ ] Snapshot creation
- [ ] Metadata storage
- [ ] Gallery view
- [ ] Search/filter

### Phase 4: Polish
- [ ] GoS branding
- [ ] UI/UX improvements
- [ ] Documentation
- [ ] Testing

---

## Data Models

### Experiment
```json
{
  "id": "experiment-1",
  "name": "Experiment A - Streaming Test",
  "devices": ["device1", "device2", ...],
  "created_at": "2024-01-15T10:00:00",
  "description": "Testing HLS vs DASH"
}
```

### Snapshot
```json
{
  "id": "snapshot-1",
  "title": "Baseline Measurement",
  "experiment_id": "experiment-1",
  "time_range": {"start": "...", "end": "..."},
  "annotations": [...],
  "chart_config": {...},
  "energy_stats": {
    "total_kwh": 1.5,
    "average_watts": 125
  },
  "created_at": "2024-01-15T11:00:00"
}
```

### Annotation
```json
{
  "id": "ann-1",
  "timestamp": "2024-01-15T10:30:00",
  "label": "Started HLS stream",
  "description": "Began streaming HLS content",
  "color": "blue",
  "experiment_id": "experiment-1"
}
```

---

## Next Steps

1. Create new exploration UI structure
2. Build chart visualization component
3. Implement experiment management
4. Add annotation system
5. Build snapshot/archive system
6. Apply GoS branding

Let's build this! 🚀

