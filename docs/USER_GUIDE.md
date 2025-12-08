# GOS REM Data Exploration Tool - User Guide

## Overview

The GOS REM Data Exploration Tool is an interactive web interface for analyzing energy consumption data collected from TP-Link Tapo P110 smart plugs. This guide will help you navigate and use all the features effectively.

## Getting Started

### Accessing the Tool

1. Open your web browser
2. Navigate to the main interface (default: http://localhost:7001)
3. The page will automatically load with a default chart showing all devices from the last hour

### Navigation Menu

The top navigation bar provides quick access to:
- **Groups**: Manage device groups for organizing experiments
- **Experiments**: Create and manage experiments (time-based studies)
- **Gallery**: View saved chart snapshots

## Main Exploration Page

### Chart View

The main exploration page displays interactive charts for analyzing your data.

#### Chart A and Chart B

- **Chart A**: Primary chart view (always visible)
- **Chart B**: Secondary chart for comparison (can be overlaid or split)
- **Toggle Split Charts**: Use the "Split Charts" checkbox to overlay or separate Chart A and B

#### Default Chart

On first load, the system automatically displays:
- All available devices
- Last 1 hour of data
- Real-time updates every 30 seconds

### Controls Panel

#### Time Range Selection

Choose how much historical data to display:
- **Last 15 minutes**: Quick view of recent activity
- **Last 1 hour**: Default view
- **Last 6 hours**: Half-day view
- **Last 24 hours**: Full day
- **Last 7 days**: Weekly view (auto-adjusts aggregation)
- **Last 30 days**: Monthly view (auto-adjusts aggregation)
- **Custom Range**: Select specific start and end times
- **Use Experiment Range**: For experiments, automatically use the experiment's time span

#### Aggregation Interval

Control the granularity of data points:
- **10 seconds**: Highest detail (only for short time ranges)
- **30 seconds**: High detail
- **1 minute**: Standard detail
- **5 minutes**: Medium detail
- **15 minutes**: Lower detail
- **30 minutes**: Very low detail
- **1 hour**: Hourly aggregation
- **6 hours**: 6-hour buckets
- **12 hours**: 12-hour buckets
- **1 day**: Daily aggregation

**Note**: The system automatically adjusts aggregation for large time ranges to prevent timeouts. For example, 7-day views will automatically use 1-hour intervals.

#### Curve Type

Choose how data points are connected:
- **Linear**: Straight lines between points
- **Monotone**: Smooth curves using cubic interpolation
- **Step**: Step functions (staircase effect)

#### Statistical Overlays

Toggle visibility of calculated statistics:
- **Mean**: Average power across selected devices
- **Median**: Middle value across selected devices
- **Total**: Sum of power from all selected devices
- **Average**: Same as mean (included for clarity)

**Tip**: Use the legend to show/hide individual devices, and the statistics will automatically recalculate based on visible devices only.

#### Live Updates

- **Pause/Resume Live Update**: Toggle automatic chart refreshing
- Charts refresh every 30 seconds when live updates are enabled
- When paused, the view is locked for detailed analysis

### Experiment Controls

#### Selecting Experiments and Groups

1. **For Chart A or Chart B**:
   - Select an experiment from the dropdown
   - Select one or more groups from that experiment's linked groups
   - The chart will automatically load data for those groups within the experiment's time range

2. **For Current Experiments**:
   - Mark an experiment as "Current" when creating it
   - Use "Start Experiment" to begin data collection
   - Use "End Experiment" to mark completion
   - Start time is automatically set to "now" when started
   - End time is automatically set to "now" when ended

#### Creating Experiments

1. Navigate to **Experiments** in the menu
2. Click "Create New Experiment"
3. Fill in:
   - **Name**: Descriptive name (e.g., "Encoder Modelling Test")
   - **Description**: Optional details about the experiment
   - **Start Time**: When the experiment begins (or leave blank for "now")
   - **End Time**: When it ends (or leave blank for ongoing)
   - **Is Current**: Check if this is an active experiment
   - **Linked Groups**: Select one or more device groups to include

### Data Collection Controls

#### Collector Status

View and control the data collection service:
- **Status Indicator**: Green dot = Running, Red dot = Stopped
- **Current Polling Interval**: Shows how often data is collected (in seconds)
- **Enable/Disable**: Start or stop data collection
- **Set Polling Frequency**: Adjust collection interval (10-300 seconds)

**Recommendations**:
- 30 seconds: Standard rate (recommended)
- 10 seconds: High-frequency monitoring (may hit API limits)
- 60+ seconds: Lower frequency (saves API quota)

## Device Groups Management

### Creating Groups

1. Navigate to **Groups** in the menu
2. Enter a group name (e.g., "Display Devices", "Encoder Group A")
3. Click "Create Group"
4. Select devices to add to the group
5. Click "Save Group"

### Editing Groups

1. Find the group in the "Existing Groups" list
2. Click the **Edit** button
3. Modify the group name or device membership
4. Click "Save Changes"

### Deleting Groups

1. Find the group in the "Existing Groups" list
2. Click the **Delete** button
3. Confirm deletion

**Note**: Deleting a group does not delete data. It only removes the grouping.

## Experiments Management

### Creating Experiments

See "Creating Experiments" under Experiment Controls above.

### Editing Experiments

1. Navigate to **Experiments**
2. Find the experiment in the list
3. Click **Edit**
4. Modify any details
5. Click "Save Changes"

### Starting/Ending Current Experiments

1. On the main exploration page
2. Select a "Current" experiment in Chart A or Chart B
3. Use the **Start Experiment** or **End Experiment** buttons
4. The experiment's time range will be updated automatically

## Chart Interactions

### Zooming and Panning

- **Zoom**: Scroll with mouse wheel or pinch on trackpad
- **Pan**: Click and drag to move the time axis
- **Reset**: Double-click the chart to reset zoom

### Legend Interactions

- **Show/Hide Devices**: Click on a device name in the legend to toggle visibility
- **Statistical Recalculation**: When devices are hidden, Mean/Median/Total automatically recalculate
- **Tooltip**: Hover over lines to see exact values

### Selecting Time Ranges

1. Zoom/pan to your desired time range
2. Statistics (Total, Average, Mean, Median) update automatically based on visible range
3. Use the time range dropdown to quickly jump to preset ranges

## Annotations

### Adding Annotations

1. Navigate to the time point you want to annotate
2. Click the "Add Annotation" button
3. Enter your note
4. The timestamp is automatically set to the current view's time

### Viewing Annotations

- Annotations appear as small dots under the timeline
- Hover over a dot to see the annotation text
- Click on a dot to see full details

## Snapshots

### Taking Snapshots

1. Set up your chart view (experiments, groups, time range, etc.)
2. Click "Save Snapshot"
3. Fill in:
   - **Experiment**: Select the experiment this snapshot relates to
   - **Notes**: Optional description
4. Click "Save"

### Viewing Snapshots

1. Navigate to **Gallery** in the menu
2. Browse saved snapshots
3. Click on a snapshot to view full details
4. Use fullscreen mode for detailed analysis
5. Download snapshots for reports

### Snapshot Features

- **Fullscreen View**: Click the fullscreen icon for detailed analysis
- **Download**: Download snapshot images for reports
- **Search**: Filter snapshots by experiment or date
- **Details**: View experiment, groups, time range, and notes

## Tips and Best Practices

### For A/B Testing

1. Create two groups (e.g., "Group A" and "Group B")
2. Create an experiment and link both groups
3. Select the experiment for Chart A, choose "Group A"
4. Select the same experiment for Chart B, choose "Group B"
5. Enable "Split Charts" to compare side-by-side
6. Use the same time range for both charts

### For Large Time Ranges

- The system automatically adjusts aggregation to prevent timeouts
- For 7+ days, expect 1-hour aggregation
- For 3-7 days, expect 15-minute aggregation
- Adjust the aggregation dropdown if you need different granularity

### For Performance

- Pause live updates when analyzing historical data
- Use larger aggregation intervals for long time ranges
- Hide unused devices in the legend to improve chart performance

### For Data Quality

- Check collector status regularly
- Monitor polling interval
- Use annotations to mark significant events
- Take snapshots before making configuration changes

## Troubleshooting

### Charts Not Loading

1. Check collector status (should be "Running")
2. Verify devices are collecting data
3. Try a shorter time range
4. Check browser console for errors

### No Data Showing

1. Verify data collection is enabled
2. Check if devices have data for the selected time range
3. Try expanding the time range
4. Check database connection (see admin logs)

### Slow Performance

1. Increase aggregation interval
2. Reduce time range
3. Hide unused devices in legend
4. Pause live updates

### Statistics Look Wrong

1. Check which devices are visible in the legend
2. Statistics recalculate based on visible devices only
3. Unhide all devices to see full totals

## Keyboard Shortcuts

- **Escape**: Exit fullscreen mode
- **Mouse Wheel**: Zoom in/out
- **Click + Drag**: Pan chart

## Support

For technical issues:
- Check the main README.md for deployment and configuration help
- Review logs: `docker-compose logs admin`
- Check collector logs: `docker-compose logs collector`

---

**Last Updated**: 2025-12-08  
**Version**: 1.1.0

