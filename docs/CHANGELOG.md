# Changelog

All notable changes to the GOS REM system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.2] - 2026-03-25

### Added
- **TP-Link adaptive backoff**: detects HTTP **429**, **503**, and rate-limit style API messages; automatically increases sleep between rounds, reduces parallel workers, and adds inter-chunk delay (without editing saved UI settings). Recovers stepwise after several clean cycles (`COLLECTOR_BACKOFF_RECOVER_STREAK`, default 3).
- **`collector_status.json`** (next to `collector_control.json`): runtime health (`ok` / `recovering` / `throttled`), effective vs configured settings, counters. Exploration UI **TP-Link cloud / throttling** panel; **Reset throttle** touches `reset_backoff`; **Adaptive backoff** toggle (`adaptive_backoff` in control JSON).
- **`POST /api/collector/control`**: optional `adaptive_backoff`, `reset_backoff` (no container restart unless interval/workers/delay/enabled change).

### Changed
- **docker-compose**: collector mounts `admin-data` **read-write** and sets **`COLLECTOR_STATUS_FILE`** so the collector can write status and read throttle reset. **`docker-compose.nas.yml`**: admin mount rw + status env.

## [1.5.1] - 2026-03-25

### Added
- **`app/benchmark_poll_cycle.py`**: measures mean **round duration** (device list + all power reads, no DB writes). Reports **effective cadence** ≈ round + `poll_interval` vs a target (default 10s). Optional **`--sweep`** tries multiple `parallel_workers` values and suggests the fastest stable setting. **`scripts/run_benchmark_poll.sh`** runs it inside the collector container.

### Changed
- Collector: polling logic extracted to **`collect_power_readings()`** for reuse by the benchmark (behavior unchanged).

## [1.5.0] - 2026-03-25

### Added
- Collector: **parallel TP-Link polling** via `ThreadPoolExecutor` — chunks of up to `parallel_workers` (1–32, default 8) concurrent requests; `device_query_delay` sleeps **between chunks** when parallel is greater than 1.
- `collector_control.json` / UI: `parallel_workers`; env `COLLECTOR_PARALLEL_WORKERS` overrides JSON when set.

### Changed
- Exploration: controls and copy for parallel workers; device delay help text clarifies chunk vs sequential behavior.

## [1.4.7] - 2026-03-25

### Changed
- Exploration UI and experiment export `README_export.txt`: document that poll interval is **pause between full collection rounds** (all devices sequentially); per-device sample period ≈ round duration + interval, not the interval alone.

## [1.4.6] - 2026-03-24

### Fixed
- Collector ignored Exploration UI **poll interval** because `collector_control.json` lived on the **admin** Docker volume while the collector only saw the **collector** volume. Compose now mounts `admin-data` at `/app/data/admin` (read-only) in the collector service with `COLLECTOR_CONTROL_FILE=/app/data/admin/collector_control.json`. The collector applies `poll_interval` from that file each loop (overrides env/yaml).

## [1.4.5] - 2026-03-24

### Added
- Collector: `POLL_INTERVAL` environment variable now overrides `config.yaml` `poller.interval` (Docker Compose supplied it previously but the collector ignored it).

### Changed
- Experiment export ZIP `README_export.txt`: clarify that row spacing follows collector poll interval, not chart aggregation.

## [1.4.4] - 2026-03-24

### Fixed
- Experiment full ZIP export: `can't compare offset-naive and offset-aware datetimes` when `time_range.start`/`end` from JSON lacked a timezone. Parsing now treats naive values as UTC and normalizes to aware UTC for comparisons and queries.

## [1.4.3] - 2026-03-24

### Fixed
- HTML pages returning 500 after Starlette 1.x: `TemplateResponse` now called as `(request, template_name, context)` everywhere in `admin/app.py` (see Starlette `Jinja2Templates` API).

## [1.4.2] - 2026-03-24

### Added
- **Experiment full data export**: ZIP download with `power_readings.csv` (raw `gos_rem` rows, batched query), `experiment_metadata.json`, `annotations.json`, and `README_export.txt` documenting raw vs aggregated chart data.
- **API**: `GET /api/experiments/{experiment_id}/export`.
- **Redirect**: `GET /experiment` → `/experiments` (307).

### Changed
- Experiments list UI: “Download all data” button per experiment; help text on Experiments and Exploration pages about aggregation vs full export.

## [1.4.1] - 2026-03-23

### Fixed
- Collector: recover from TP-Link **token invalid** (`-10902`) by refreshing OAuth token and retrying; prefer persisted refresh token file for rotation.

### Changed
- Removed token value prints from collector logs.

## [1.4.0] - 2026-03-11

### Added
- Production deployment documentation for Akamai Linode; optional HTTP Basic Auth (`ADMIN_BASIC_USER` / `ADMIN_BASIC_PASSWORD`); Caddy for HTTPS (Let's Encrypt).

### Changed
- README and deployment targets: Linode production, Pi400 dev/staging.

## [1.3.2] - 2025-12-17

### Removed
- Grafana service (no longer used - replaced by custom admin UI)
- InfluxDB service and native installation (migrated to TimescaleDB)
- All Grafana-related configuration and documentation

### Changed
- Cleaned up docker-compose.yml to remove unused services
- Updated documentation to reflect TimescaleDB-only architecture
- Freed ~6GB disk space on production server (removed orphaned Docker images and old InfluxDB data)

## [1.3.1] - 2025-12-17

### Added
- Device Query Delay setting in UI (configurable 0-5 seconds between API calls)
- Prevents TP-Link API rate limiting (429 errors) with configurable delay

### Fixed
- Collector hanging after API rate limit errors (now recoverable)
- Data collection gap caused by rate limiting on Dec 15-17

### Changed
- Default device query delay set to 0.5 seconds
- Collector now reads delay setting from control file dynamically

## [1.3.0] - 2025-12-13

### Added
- Horizontal scrollbar for zoomed charts (appears when zoomed in)
- CSV data export in snapshot ZIP downloads (raw power consumption data)

### Fixed
- Snapshot ZIP downloads now include CSV file with raw data
- CSV generation fixed (was failing due to text/bytes encoding issue)

### Changed
- Improved chart zoom/pan controls with scrollbar navigation
- Snapshot downloads now contain three files: PNG image, CSV data, and JSON metadata

### User Feedback (Ben)
Based on user feedback from Ben:
- Added scrollbar for easier navigation when zoomed in
- Enhanced snapshot exports with raw CSV data for external analysis
- Improved overall chart interaction experience

## [1.2.0] - 2025-12-12

### Added
- Database export/import functionality via Admin interface
- Grafana-like device selection (single-click select one, shift-click toggle)
- Snapshot ZIP downloads (image + CSV + metadata)
- Chart B statistical overlays in split mode
- Experiment reactivation (clear end dates to make current)
- Admin page in navigation menu

### Fixed
- Chart B statistical overlays not working in split mode
- Gallery download button not working
- Gallery layout breaking with long experiment details
- Experiment reactivation not working
- Pan mode only working horizontally (now supports xy)
- Alert spam during auto-refresh failures

### Changed
- Improved pan/zoom controls (xy panning support)
- Enhanced error handling for consecutive API failures
- Better UI feedback with progress indicators for export/import
- Improved validation for destructive operations

## [1.1.0] - 2025-12-08

### Added
- Smart aggregation (automatic interval adjustment)
- Query optimization for large datasets (>50k points)
- 7-day and 30-day time range options
- Live auto-refreshing charts with pause/resume
- Better error messages and timeout handling
- 5-minute query timeout configuration

### Fixed
- 502/504 timeout errors for large time ranges
- Time range dropdown not updating charts
- Aggregation dropdown not applying changes
- JSON parsing errors on failed requests
- MutationObserver errors in Chart.js
- Database password configuration issues

### Changed
- Optimized time bucket generation for large datasets
- Improved fetch error handling with proper JSON parsing
- Added request abort controllers for timeout management

## [1.0.0] - 2025-12-06

### Added
- Initial release of Docker-based containerized system
- Migration from InfluxDB to TimescaleDB
- GOS REM Data Exploration Tool with interactive charts
- Experiment management system with device grouping
- Snapshot gallery with annotations
- Collector control via web UI
- Default chart loading with all devices
- Full GoS branding with logo and colors

### Migration Notes
- Legacy InfluxDB data can be migrated using forward-fill script
- Old native InfluxDB/Grafana installation on Pi400 has been decommissioned

