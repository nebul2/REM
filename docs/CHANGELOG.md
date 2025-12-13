# Changelog

All notable changes to the GOS REM system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

