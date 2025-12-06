# GOS REM Data Exploration UI - Full Specification

## Vision

Transform the admin UI into a comprehensive data exploration tool for GOS REM streaming energy experiments. The collector remains a "data logger" - this new UI reads from InfluxDB to explore, analyze, annotate, and archive experiments.

---

## Architecture

```
┌─────────────────┐
│  Data Collector │  ← Data Logger (unchanged)
│  (Data Logger)  │     Writes to InfluxDB
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    InfluxDB     │  ← Time-series database
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│   GOS REM Exploration UI (NEW)      │  ← Custom-built exploration tool
│                                     │
│   • Experiment Management           │
│   • Data Visualization              │
│   • A/B Comparison                  │
│   • Statistical Analysis            │
│   • Timeline Annotations            │
│   • Snapshot Gallery                │
│   • GoS Branding                    │
└─────────────────────────────────────┘
```

---

## Core Features

### 1. Experiment/Group Management
- **Create experiments** with device groups
- **Filter by experiment** - only show selected devices
- **A/B testing** - Compare two experiments side-by-side
- **Re-run experiments** - Change group membership, analyze same time range
- **Experiment library** - Browse all created experiments

### 2. Data Visualization
- **Time-series charts** - Power consumption over time (Chart.js/D3.js)
- **Multiple devices** - All devices in experiment as separate lines
- **Statistical overlays** - Toggle mean, median, min, max, std dev
- **Aggregate lines** - Total (sum) and average across all devices
- **Zoom/Pan** - Interactive chart controls
- **Time range selection** - Last 15m, 1h, 6h, 24h, custom range

### 3. Energy Calculations
- **Total energy** - Sum of all devices over time range (kWh)
- **Average energy** - Mean power across devices (W)
- **Per-device totals** - Individual device energy consumption
- **Comparison metrics** - Energy difference between A/B experiments
- **Display** - Real-time stats panel with all calculations

### 4. Timeline Annotations
- **Add annotations** - Click on timeline to mark test points
- **Edit/delete** - Manage annotations
- **Colored markers** - Different colors for test types
- **Rich descriptions** - Title, description, test details
- **Visibility toggle** - Show/hide annotations
- **Export** - Annotations saved with snapshots

### 5. Snapshot & Archive Gallery
- **Save snapshots** - Capture current chart state
- **Metadata** - Title, description, experiment name, time range, annotations
- **Gallery view** - Grid/list view of all snapshots
- **Filter/search** - By experiment, date, device, annotation text
- **Compare snapshots** - Side-by-side view
- **Export** - Download as PNG/PDF
- **Recall experiments** - Find historic charts for reference

### 6. GoS Branding
- **Logo** - GoS logo in header/nav
- **Color scheme** - Green/white theme matching logo
- **Favicon** - GoS logo
- **Theming** - Consistent branding throughout

---

## UI Layout

### Main Dashboard
```
┌──────────────────────────────────────────────────────────────────┐
│  [GoS Logo]  GOS Remote Energy Measurement - Data Exploration   │
├──────────────────────────────────────────────────────────────────┤
│  Experiments:                                                    │
│  [Select A ▼] [Select B ▼] [Create Experiment] [Manage]        │
│                                                                  │
│  Time Range: [Last 1h ▼] [Custom: Start] [End] [Apply]        │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────┐  ┌──────────────────────────┐    │
│  │  Experiment A            │  │  Experiment B            │    │
│  │  ┌────────────────────┐  │  │  ┌────────────────────┐  │    │
│  │  │                    │  │  │  │                    │  │    │
│  │  │   [Power Chart]    │  │  │  │   [Power Chart]    │  │    │
│  │  │                    │  │  │  │                    │  │    │
│  │  └────────────────────┘  │  │  └────────────────────┘  │    │
│  │                          │  │                          │    │
│  │  Stats:                  │  │  Stats:                  │    │
│  │  Total: 1.5 kWh          │  │  Total: 2.1 kWh          │    │
│  │  Avg: 125 W              │  │  Avg: 175 W              │    │
│  │  Mean: 120 W             │  │  Mean: 170 W             │    │
│  │  Median: 115 W           │  │  Median: 165 W           │    │
│  └──────────────────────────┘  └──────────────────────────┘    │
├──────────────────────────────────────────────────────────────────┤
│  Controls:                                                       │
│  [✓ Mean] [✓ Median] [✓ Total] [✓ Average] [Show All Stats]    │
│                                                                  │
│  [📌 Add Annotation] [💾 Save Snapshot] [📊 Gallery] [⚙️ Settings] │
└──────────────────────────────────────────────────────────────────┘
```

### Gallery View
```
┌──────────────────────────────────────────────────────────────────┐
│  [GoS Logo]  GOS REM - Snapshot Gallery                          │
├──────────────────────────────────────────────────────────────────┤
│  Filter: [All Experiments ▼] [Date Range] [Search...]            │
├──────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ [Image]  │  │ [Image]  │  │ [Image]  │  │ [Image]  │        │
│  │          │  │          │  │          │  │          │        │
│  │ Baseline │  │ Test 1   │  │ Test 2   │  │ Compare  │        │
│  │ 1h ago   │  │ 2h ago   │  │ 3h ago   │  │ 4h ago   │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└──────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Backend
- **FastAPI** - REST API for data queries
- **InfluxDB Client** - Read time-series data
- **JSON/SQLite** - Store experiments, annotations, snapshots

### Frontend
- **HTML/CSS/JavaScript** - Modern vanilla JS (or React if needed)
- **Chart.js** or **D3.js** - Data visualization
- **GoS Branding** - Logo, colors, favicon

### Storage
- **Experiments** - JSON file or SQLite
- **Snapshots** - JSON metadata + PNG images
- **Annotations** - Stored with experiments/snapshots

---

## Data Models

### Experiment
```json
{
  "id": "exp-001",
  "name": "Experiment A - HLS Streaming",
  "description": "Testing HLS encoding energy consumption",
  "devices": ["device1", "device2", "device3"],
  "created_at": "2024-01-15T10:00:00",
  "updated_at": "2024-01-15T10:00:00"
}
```

### Snapshot
```json
{
  "id": "snap-001",
  "title": "Baseline Measurement",
  "description": "Initial power consumption before test",
  "experiment_id": "exp-001",
  "time_range": {
    "start": "2024-01-15T10:00:00",
    "end": "2024-01-15T11:00:00"
  },
  "annotations": ["ann-001", "ann-002"],
  "chart_config": {
    "show_mean": true,
    "show_median": true,
    "show_total": true
  },
  "energy_stats": {
    "total_kwh": 1.5,
    "average_watts": 125,
    "mean_watts": 120,
    "median_watts": 115
  },
  "image_path": "snapshots/snap-001.png",
  "created_at": "2024-01-15T11:00:00"
}
```

### Annotation
```json
{
  "id": "ann-001",
  "timestamp": "2024-01-15T10:30:00",
  "label": "Started HLS Stream",
  "description": "Began streaming HLS content at 1080p",
  "color": "#007bff",
  "experiment_id": "exp-001"
}
```

---

## Implementation Plan

### Phase 1: Foundation (Week 1)
1. ✅ FastAPI backend structure
2. [ ] Chart.js integration
3. [ ] Basic experiment management
4. [ ] InfluxDB data reading API

### Phase 2: Core Features (Week 1-2)
5. [ ] Time-series chart visualization
6. [ ] Statistical overlays (mean/median)
7. [ ] Energy calculations
8. [ ] A/B comparison view

### Phase 3: Advanced Features (Week 2)
9. [ ] Timeline annotations
10. [ ] Snapshot creation
11. [ ] Gallery view
12. [ ] Search/filter

### Phase 4: Polish (Week 2-3)
13. [ ] GoS branding (logo, colors)
14. [ ] UI/UX improvements
15. [ ] Documentation
16. [ ] Testing

---

## Next Steps

1. Create new UI structure (transform admin UI)
2. Integrate chart library
3. Build experiment management
4. Add annotation system
5. Build snapshot/archive
6. Apply GoS branding

Let's build this! 🚀

