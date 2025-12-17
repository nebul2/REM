// GOS REM Data Exploration - Complete JavaScript

// Global state
let chartA = null;
let chartB = null;
let currentExperimentA = null;
let currentExperimentB = null;
let currentGroupsA = []; // Selected groups for Chart A
let currentGroupsB = []; // Selected groups for Chart B
let currentTimeRange = '1h';
let currentAggregation = '1m';
let allDevices = [];
let groups = {}; // Device groups (participant groups)
let experiments = {}; // Time-based experiments with ranges and group links
let annotations = {};
let annotationPopups = {}; // Track open annotation popups
let showDevices = true;
let showMean = true;
let showMedian = true;
let showTotal = true;
let showAverage = true;

// Store chart data for recalculation when legend items are toggled
let chartDataA = null; // {data, devices, stats, experiment}
let chartDataB = null;
let splitCharts = false; // false = overlay mode (default), true = split mode
let curveType = 'smooth'; // Options: 'linear', 'smooth', 'monotone', 'step', 'stepped-after'
let autoUpdate = true; // Auto-update chart with new data (default: enabled)
let updateInterval = null; // Store the auto-update interval

// Colors for device lines
const deviceColors = [
    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
    '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384'
];

// Register Chart.js plugins
if (typeof Chart !== 'undefined') {
    // Zoom plugin auto-registers when loaded via CDN, but ensure it's available
    console.log('Chart.js loaded, plugins available:', Object.keys(Chart.registry?.plugins || {}));
}

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Initializing GOS REM Exploration Tool...');
    try {
        await loadInitialData();
        setupEventListeners();
        initializeCharts();
        
        // Chart B is already hidden by default in HTML (overlay mode)
        // Set up overlay mode after a brief delay to ensure charts are ready
        if (!splitCharts) {
            setTimeout(() => {
                toggleOverlay();
            }, 200);
        }
        
        console.log('Initialization complete. Experiments:', Object.keys(experiments).length);
        
        // Load default chart with all devices showing last hour
        if (allDevices.length > 0) {
            setTimeout(() => {
                loadDefaultChart();
                // Start auto-update after initial chart loads
                startAutoUpdate();
            }, 500);
        } else {
            // Start auto-update even if no devices yet
            startAutoUpdate();
        }
    } catch (error) {
        console.error('Initialization error:', error);
    }
});

// Load initial data
async function loadInitialData() {
    try {
        console.log('Loading devices...');
        // Load devices
        const devicesRes = await fetch('/api/devices');
        if (!devicesRes.ok) {
            throw new Error(`Failed to load devices: ${devicesRes.status}`);
        }
        const devicesData = await devicesRes.json();
        allDevices = devicesData.devices || [];
        console.log(`Loaded ${allDevices.length} devices`);
        
        // Load groups (for linking to experiments)
        console.log('Loading groups...');
        const groupsRes = await fetch('/api/groups');
        if (!groupsRes.ok) {
            throw new Error(`Failed to load groups: ${groupsRes.status}`);
        }
        const groupsData = await groupsRes.json();
        groups = groupsData.groups || {};
        console.log(`Loaded ${Object.keys(groups).length} groups:`, Object.keys(groups));
        
        // Load experiments (time-based studies with group links)
        console.log('Loading experiments...');
        const experimentsRes = await fetch('/api/experiments');
        if (!experimentsRes.ok) {
            throw new Error(`Failed to load experiments: ${experimentsRes.status}`);
        }
        const experimentsData = await experimentsRes.json();
        experiments = experimentsData.experiments || {};
        console.log(`Loaded ${Object.keys(experiments).length} experiments:`, Object.keys(experiments));
        
        populateExperimentSelects();
        populateGroupCheckboxes();
        
        // Load annotations
        await loadAnnotations();
    } catch (error) {
        console.error('Error loading initial data:', error);
        alert(`Error loading data: ${error.message}. Please check the console for details.`);
    }
}

// Load annotations from API
async function loadAnnotations() {
    try {
        const response = await fetch('/api/annotations');
        if (response.ok) {
            const data = await response.json();
            annotations = data.annotations || {};
            console.log(`Loaded ${Object.keys(annotations).length} annotations`);
        }
    } catch (error) {
        console.error('Error loading annotations:', error);
    }
}

// Setup event listeners
function setupEventListeners() {
    // Chart A experiment selection
    document.getElementById('chartAExperiment').addEventListener('change', (e) => {
        currentExperimentA = e.target.value;
        if (currentExperimentA) {
            populateGroupsForChart('A', currentExperimentA);
            // If it's a current experiment without a start time, set it to now
            const experiment = experiments[currentExperimentA];
            if (experiment && experiment.is_current) {
                if (!experiment.time_range || !experiment.time_range.start) {
                    // Auto-set start time to now for current experiments
                    if (!experiment.time_range) experiment.time_range = {};
                    experiment.time_range.start = new Date().toISOString();
                    // Update experiment in backend
                    updateExperimentStartTime(currentExperimentA, experiment.time_range.start);
                }
            }
            // Auto-set time range if experiment has a time range
            autoSetTimeRangeForExperiment(currentExperimentA);
            // Load data after groups are populated (use setTimeout to ensure groups are set)
            setTimeout(() => {
                if (currentGroupsA.length > 0) {
                    loadChartData('A');
                }
            }, 10);
        } else {
            populateGroupsForChart('A', null);
            currentGroupsA = [];
            if (chartA) chartA.destroy();
            chartA = null;
        }
    });
    
    // Chart A group checkboxes are handled by updateSelectedGroups() in populateGroupsForChart
    // Checkboxes have individual change handlers that call updateSelectedGroups()
    
    // Chart B experiment selection
    document.getElementById('chartBExperiment').addEventListener('change', (e) => {
        currentExperimentB = e.target.value;
        if (currentExperimentB) {
            populateGroupsForChart('B', currentExperimentB);
            // Auto-set time range if experiment has a time range
            autoSetTimeRangeForExperiment(currentExperimentB);
            // If it's a current experiment without a start time, set it to now
            const experiment = experiments[currentExperimentB];
            if (experiment && experiment.is_current) {
                if (!experiment.time_range || !experiment.time_range.start) {
                    // Auto-set start time to now for current experiments
                    if (!experiment.time_range) experiment.time_range = {};
                    experiment.time_range.start = new Date().toISOString();
                    // Update experiment in backend
                    updateExperimentStartTime(currentExperimentB, experiment.time_range.start);
                }
            }
            // Load data after groups are populated (use setTimeout to ensure groups are set)
            setTimeout(() => {
                if (currentGroupsB.length > 0) {
                    loadChartData('B');
                }
            }, 10);
        } else {
            populateGroupsForChart('B', null);
            currentGroupsB = [];
            if (chartB) chartB.destroy();
            chartB = null;
        }
    });
    
    // Chart B group checkboxes are handled by updateSelectedGroups() in populateGroupsForChart
    // Checkboxes have individual change handlers that call updateSelectedGroups()
    
    document.getElementById('timeRange').addEventListener('change', (e) => {
        const newTimeRange = e.target.value;
        currentTimeRange = newTimeRange;
        console.log(`Time range changed to: ${currentTimeRange}`);
        
        if (currentTimeRange === 'custom') {
            document.getElementById('customRange').style.display = 'flex';
        } else {
            document.getElementById('customRange').style.display = 'none';
            // Always reload charts when time range changes (if data exists)
            // Check for default chart first (by ID or by checking if allDevices are loaded)
            const isDefaultChart = chartDataA && chartDataA.experiment && chartDataA.experiment.id === 'all-devices';
            if (isDefaultChart) {
                // Reload default chart with new time range (don't call loadDefaultChart which resets to 1h)
                console.log('Reloading default chart with new time range...');
                reloadDefaultChartWithCurrentTimeRange();
            } else if (currentExperimentA && currentGroupsA.length > 0) {
                console.log('Reloading Chart A with new time range...');
                loadChartData('A');
            } else {
                console.warn('No chart to reload - currentExperimentA:', currentExperimentA, 'chartDataA:', !!chartDataA);
            }
            if (splitCharts && currentExperimentB && currentGroupsB.length > 0) {
                console.log('Reloading Chart B with new time range...');
                loadChartData('B');
            }
        }
    });
    
    document.getElementById('applyCustomRange').addEventListener('click', () => {
        if (currentExperimentA && currentGroupsA.length > 0) loadChartData('A');
        if (currentExperimentB && currentGroupsB.length > 0) loadChartData('B');
    });
    
    document.getElementById('aggregation').addEventListener('change', (e) => {
        currentAggregation = e.target.value;
        console.log(`Aggregation changed to: ${currentAggregation}`);
        // Always reload charts when aggregation changes (if data exists)
        // Check for default chart first
        const isDefaultChart = chartDataA && chartDataA.experiment && chartDataA.experiment.id === 'all-devices';
        if (isDefaultChart) {
            // Reload default chart with current time range
            console.log('Reloading default chart with new aggregation...');
            reloadDefaultChartWithCurrentTimeRange();
        } else if (currentExperimentA && currentGroupsA.length > 0) {
            console.log('Reloading Chart A with new aggregation...');
            loadChartData('A');
        } else {
            console.warn('No chart to reload - currentExperimentA:', currentExperimentA, 'chartDataA:', !!chartDataA);
        }
        if (splitCharts && currentExperimentB && currentGroupsB.length > 0) {
            console.log('Reloading Chart B with new aggregation...');
            loadChartData('B');
        }
    });
    
    document.getElementById('curveType').addEventListener('change', (e) => {
        curveType = e.target.value;
        updateCharts();
    });
    
    // Statistical toggles
    document.getElementById('showDevices').addEventListener('change', (e) => {
        showDevices = e.target.checked;
        updateCharts();
    });
    
    document.getElementById('showMean').addEventListener('change', (e) => {
        showMean = e.target.checked;
        console.log('Toggle Mean:', showMean);
        try {
            if (typeof updateCharts === 'function') {
                updateCharts();
            } else {
                console.error('updateCharts is not a function!');
            }
        } catch (error) {
            console.error('Error in showMean toggle:', error);
        }
    });
    
    document.getElementById('showMedian').addEventListener('change', (e) => {
        showMedian = e.target.checked;
        console.log('Toggle Median:', showMedian);
        try {
            if (typeof updateCharts === 'function') {
                updateCharts();
            } else {
                console.error('updateCharts is not a function!');
            }
        } catch (error) {
            console.error('Error in showMedian toggle:', error);
        }
    });
    
    document.getElementById('showTotal').addEventListener('change', (e) => {
        showTotal = e.target.checked;
        console.log('Toggle Total:', showTotal);
        try {
            if (typeof updateCharts === 'function') {
                updateCharts();
            } else {
                console.error('updateCharts is not a function!');
            }
        } catch (error) {
            console.error('Error in showTotal toggle:', error);
        }
    });
    
    document.getElementById('showAverage').addEventListener('change', (e) => {
        showAverage = e.target.checked;
        console.log('Toggle Average:', showAverage);
        try {
            if (typeof updateCharts === 'function') {
                updateCharts();
            } else {
                console.error('updateCharts is not a function!');
            }
        } catch (error) {
            console.error('Error in showAverage toggle:', error);
        }
    });
    
    document.getElementById('splitCharts').addEventListener('change', (e) => {
        splitCharts = e.target.checked;
        toggleOverlay();
    });
    
    // Auto-update toggle button
    const autoUpdateBtn = document.getElementById('autoUpdateBtn');
    if (autoUpdateBtn) {
        autoUpdateBtn.addEventListener('click', toggleAutoUpdate);
    }
    
    // Reset zoom button
    const resetZoomBtn = document.getElementById('resetZoomBtn');
    if (resetZoomBtn) {
        resetZoomBtn.addEventListener('click', resetZoom);
    }
    
    // Double-click on charts to reset zoom
    if (document.getElementById('chartA')) {
        document.getElementById('chartA').addEventListener('dblclick', () => {
            if (chartA) resetZoomForChart(chartA);
        });
    }
    if (document.getElementById('chartB')) {
        document.getElementById('chartB').addEventListener('dblclick', () => {
            if (chartB) resetZoomForChart(chartB);
        });
    }
    
    // Buttons
    document.getElementById('addAnnotationBtn').addEventListener('click', () => {
        openModal('addAnnotationModal');
    });
    
    document.getElementById('saveSnapshotBtn').addEventListener('click', () => {
        populateExperimentSelects(); // Ensure snapshot experiment select is populated
        openModal('saveSnapshotModal');
    });
    
    // Start/End Experiment handlers
    document.getElementById('startExperimentBtn').addEventListener('click', async () => {
        // Get currently selected experiment (Chart A takes priority)
        const experimentId = currentExperimentA || currentExperimentB;
        if (!experimentId) {
            alert('Please select an experiment first');
            return;
        }
        
        try {
            const response = await fetch(`/api/experiments/${experimentId}/start`, {
                method: 'POST'
            });
            
            if (response.ok) {
                const result = await response.json();
                experiments[experimentId] = result.experiment;
                populateExperimentSelects();
                alert(`Experiment "${result.experiment.name}" started!`);
            } else {
                const error = await response.json();
                alert(`Error: ${error.detail || 'Failed to start experiment'}`);
            }
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    });
    
    document.getElementById('endExperimentBtn').addEventListener('click', async () => {
        // Get currently selected experiment (Chart A takes priority)
        const experimentId = currentExperimentA || currentExperimentB;
        if (!experimentId) {
            alert('Please select an experiment first');
            return;
        }
        
        const experiment = experiments[experimentId];
        if (!experiment || !experiment.is_current) {
            alert('This experiment is not currently running');
            return;
        }
        
        if (!confirm(`End experiment "${experiment.name}"? This will set the end time to now.`)) {
            return;
        }
        
        try {
            const response = await fetch(`/api/experiments/${experimentId}/end`, {
                method: 'POST'
            });
            
            if (response.ok) {
                const result = await response.json();
                experiments[experimentId] = result.experiment;
                populateExperimentSelects();
                alert(`Experiment "${result.experiment.name}" ended!`);
                // Reload charts to reflect new time range
                if (currentExperimentA && currentGroupsA.length > 0) loadChartData('A');
                if (currentExperimentB && currentGroupsB.length > 0) loadChartData('B');
            } else {
                const error = await response.json();
                alert(`Error: ${error.detail || 'Failed to end experiment'}`);
            }
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    });
    
    // Collector Control
    document.getElementById('collectorEnabled').addEventListener('change', async (e) => {
        await updateCollectorEnabled(e.target.checked);
    });
    
    document.getElementById('updatePollInterval').addEventListener('click', async () => {
        const interval = parseInt(document.getElementById('pollInterval').value);
        if (interval >= 5 && interval <= 300) {
            await updatePollInterval(interval);
        } else {
            alert('Poll interval must be between 5 and 300 seconds');
        }
    });
    
    document.getElementById('updateDeviceQueryDelay').addEventListener('click', async () => {
        const delay = parseFloat(document.getElementById('deviceQueryDelay').value);
        if (delay >= 0 && delay <= 5) {
            await updateDeviceQueryDelay(delay);
        } else {
            alert('Device query delay must be between 0 and 5 seconds');
        }
    });
    
    // Load collector status on page load
    loadCollectorStatus();
    
    // Refresh collector status every 10 seconds
    setInterval(loadCollectorStatus, 10000);
    
    document.getElementById('refreshBtn').addEventListener('click', () => {
        if (currentExperimentA && currentGroupsA.length > 0) loadChartData('A');
        if (currentExperimentB && currentGroupsB.length > 0) loadChartData('B');
    });
}

// Populate experiment selects for Chart A, Chart B, and Snapshot
function populateExperimentSelects() {
    const selectA = document.getElementById('chartAExperiment');
    const selectB = document.getElementById('chartBExperiment');
    const snapshotSelect = document.getElementById('snapshotExperiment');
    
    // Clear options except first
    if (selectA) selectA.innerHTML = '<option value="">-- Select Experiment --</option>';
    if (selectB) selectB.innerHTML = '<option value="">-- Select Experiment --</option>';
    if (snapshotSelect) {
        snapshotSelect.innerHTML = '<option value="">-- Select Experiment --</option>';
    }
    
    // Show all experiments - experiments have linked_groups, groups don't
    for (const [experimentId, exp] of Object.entries(experiments)) {
        // Skip if this is actually a group (groups don't have linked_groups property)
        // Real experiments have linked_groups (even if empty array) or time_range
        if (!exp.hasOwnProperty('linked_groups') && !exp.hasOwnProperty('time_range') && !exp.is_current) {
            continue; // This is likely a group, not an experiment
        }
        
        const displayName = exp.name || experimentId;
        const timeRange = exp.time_range || {};
        const isCurrent = exp.is_current || false;
        const startDate = timeRange.start ? new Date(timeRange.start).toLocaleDateString() : '';
        const endDate = timeRange.end ? new Date(timeRange.end).toLocaleDateString() : '';
        let dateRange = '';
        let statusIndicator = '';
        if (isCurrent) {
            statusIndicator = ' 🔵 '; // Blue dot for current experiment
            dateRange = ` (Current - started ${startDate})`;
        } else if (startDate && endDate) {
            dateRange = ` (${startDate} - ${endDate})`;
        } else if (startDate) {
            dateRange = ` (started ${startDate})`;
        }
        
        if (selectA) {
            const optionA = document.createElement('option');
            optionA.value = experimentId;
            optionA.textContent = `${statusIndicator}${displayName}${dateRange}`;
            selectA.appendChild(optionA);
        }
        
        if (selectB) {
            const optionB = document.createElement('option');
            optionB.value = experimentId;
            optionB.textContent = `${statusIndicator}${displayName}${dateRange}`;
            selectB.appendChild(optionB);
        }
        
        if (snapshotSelect) {
            const optionSnapshot = document.createElement('option');
            optionSnapshot.value = experimentId;
            optionSnapshot.textContent = `${statusIndicator}${displayName}${dateRange}`;
            snapshotSelect.appendChild(optionSnapshot);
        }
    }
}

// Populate groups checkboxes for a chart based on selected experiment
function populateGroupsForChart(side, experimentId) {
    const groupsContainer = document.getElementById(`chart${side}Groups`);
    if (!groupsContainer) return;
    
    // Clear existing checkboxes
    groupsContainer.innerHTML = '';
    
    if (!experimentId) {
        groupsContainer.style.display = 'none';
        return;
    }
    
    const experiment = experiments[experimentId];
    if (!experiment) {
        groupsContainer.style.display = 'none';
        return;
    }
    
    const linkedGroups = experiment.linked_groups || [];
    if (linkedGroups.length === 0) {
        groupsContainer.innerHTML = '<p style="color: #666; font-size: 0.9rem; margin: 10px 0;">No groups linked to this experiment. Edit the experiment to add groups.</p>';
        groupsContainer.style.display = 'block';
        // Clear current groups
        if (side === 'A') {
            currentGroupsA = [];
        } else {
            currentGroupsB = [];
        }
        return;
    }
    
    // Create checkbox container
    const checkboxContainer = document.createElement('div');
    checkboxContainer.className = 'group-checkboxes';
    checkboxContainer.style.cssText = 'display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px;';
    
    // Add checkboxes for each linked group
    linkedGroups.forEach(groupName => {
        const group = groups[groupName];
        if (group) {
            const label = document.createElement('label');
            label.className = 'checkbox-label';
            label.style.cssText = 'display: flex; align-items: center; gap: 5px; cursor: pointer; padding: 5px 10px; background: #161b22; border: 1px solid #30363d; border-radius: 4px;';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = groupName;
            checkbox.checked = true; // Auto-select all by default
            checkbox.style.cssText = 'cursor: pointer;';
            
            // Add change handler to update current groups and reload chart
            checkbox.addEventListener('change', () => {
                updateSelectedGroups(side);
                // Reload chart if experiment is selected and at least one group is selected
                const selectedGroups = side === 'A' ? currentGroupsA : currentGroupsB;
                const experimentId = side === 'A' ? currentExperimentA : currentExperimentB;
                if (experimentId && selectedGroups.length > 0) {
                    loadChartData(side);
                } else if (experimentId && selectedGroups.length === 0) {
                    // Clear chart data but keep chart alive (preserves grid/scale)
                    const chart = side === 'A' ? chartA : chartB;
                    if (chart) {
                        // Clear all datasets but keep the chart structure
                        chart.data.datasets = [];
                        chart.update('none');
                        
                        // Update title to show no groups selected
                        const titleEl = document.getElementById(`chart${side}Title`);
                        if (titleEl) {
                            const experiment = experiments[experimentId];
                            const expName = experiment ? experiment.name : experimentId;
                            titleEl.textContent = `${expName} - No groups selected`;
                        }
                        
                        // Clear stats
                        const totalEl = document.getElementById(`total${side}`);
                        const avgEl = document.getElementById(`avg${side}`);
                        const meanEl = document.getElementById(`mean${side}`);
                        const medianEl = document.getElementById(`median${side}`);
                        if (totalEl) totalEl.textContent = '0';
                        if (avgEl) avgEl.textContent = '0';
                        if (meanEl) meanEl.textContent = '0';
                        if (medianEl) medianEl.textContent = '0';
                    } else {
                        // Chart doesn't exist yet - initialize it with empty data
                        initializeCharts();
                    }
                }
            });
            
            const span = document.createElement('span');
            const deviceCount = (group.devices || []).length;
            span.textContent = `${group.name || groupName} (${deviceCount} device${deviceCount !== 1 ? 's' : ''})`;
            span.style.cssText = 'font-size: 0.9rem; color: #c9d1d9;';
            
            label.appendChild(checkbox);
            label.appendChild(span);
            checkboxContainer.appendChild(label);
        }
    });
    
    groupsContainer.appendChild(checkboxContainer);
    groupsContainer.style.display = 'block';
    
    // Update the current groups array after creating checkboxes
    updateSelectedGroups(side);
}

// Update selected groups from checkboxes
function updateSelectedGroups(side) {
    const groupsContainer = document.getElementById(`chart${side}Groups`);
    if (!groupsContainer) return;
    
    const checkboxes = groupsContainer.querySelectorAll('input[type="checkbox"]:checked');
    const selectedGroups = Array.from(checkboxes).map(cb => cb.value);
    
    if (side === 'A') {
        currentGroupsA = selectedGroups;
    } else {
        currentGroupsB = selectedGroups;
    }
}

// Populate group checkboxes for experiment creation
function populateGroupCheckboxes() {
    const container = document.getElementById('experimentGroups');
    if (!container) return; // Modal might not be loaded yet
    
    container.innerHTML = '';
    
    for (const [groupName, groupData] of Object.entries(groups)) {
        const label = document.createElement('label');
        label.className = 'checkbox-label';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.name = 'groups';
        checkbox.value = groupName;
        
        const span = document.createElement('span');
        const deviceCount = (groupData.devices || []).length;
        span.textContent = `${groupData.name || groupName} (${deviceCount} device${deviceCount !== 1 ? 's' : ''})`;
        
        label.appendChild(checkbox);
        label.appendChild(span);
        container.appendChild(label);
    }
    
    if (Object.keys(groups).length === 0) {
        container.innerHTML = '<p style="color: #666; font-size: 0.9rem;">No groups found. Please create groups first in "Manage Groups".</p>';
    }
}

// Get curve configuration based on curve type
function getCurveConfig() {
    switch(curveType) {
        case 'smooth':
            return {
                tension: 0.4, // Smooth bezier curve
                cubicInterpolationMode: 'default',
                stepped: false,
                spanGaps: true // Connect across null values
            };
        case 'monotone':
            return {
                tension: 0.4,
                cubicInterpolationMode: 'monotone', // Prevents overshoot/undershoot
                stepped: false,
                spanGaps: true
            };
        case 'linear':
            return {
                tension: 0, // Straight lines between points
                cubicInterpolationMode: 'default',
                stepped: false,
                spanGaps: true
            };
        case 'step':
            return {
                tension: 0,
                stepped: 'before', // Step before the point
                spanGaps: false
            };
        case 'stepped-after':
            return {
                tension: 0,
                stepped: 'after', // Step after the point
                spanGaps: false
            };
        default:
            return {
                tension: 0.4,
                cubicInterpolationMode: 'default',
                stepped: false,
                spanGaps: true
            };
    }
}

// Get time range
function getTimeRange() {
    if (currentTimeRange === 'custom') {
        const start = document.getElementById('startTime').value;
        const end = document.getElementById('endTime').value;
        return { start, end };
    }
    
    if (currentTimeRange === 'experiment') {
        // Use experiment time range - this will be handled in loadChartData
        // For now, return a default range that will be overridden
        const now = new Date();
        return {
            start: new Date(now - 60 * 60 * 1000).toISOString(),
            end: now.toISOString()
        };
    }
    
    const now = new Date();
    let start;
    
    switch (currentTimeRange) {
        case '15m':
            start = new Date(now - 15 * 60 * 1000);
            break;
        case '1h':
            start = new Date(now - 60 * 60 * 1000);
            break;
        case '6h':
            start = new Date(now - 6 * 60 * 60 * 1000);
            break;
        case '24h':
            start = new Date(now - 24 * 60 * 60 * 1000);
            break;
        case '7d':
            start = new Date(now - 7 * 24 * 60 * 60 * 1000);
            break;
        case '30d':
            start = new Date(now - 30 * 24 * 60 * 60 * 1000);
            break;
        default:
            start = new Date(now - 60 * 60 * 1000);
    }
    
    return {
        start: start.toISOString(),
        end: now.toISOString()
    };
}

// Auto-set time range based on experiment
// Only auto-sets if user hasn't manually selected a specific time range
function autoSetTimeRangeForExperiment(experimentId) {
    const experiment = experiments[experimentId];
    if (!experiment) return;
    
    const timeRangeSelect = document.getElementById('timeRange');
    if (!timeRangeSelect) return;
    
    // Don't override if user has manually selected a specific time range
    const currentValue = timeRangeSelect.value;
    const manualRanges = ['15m', '1h', '6h', '24h', '7d', '30d', 'custom'];
    if (manualRanges.includes(currentValue)) {
        // User has manually selected a range - don't override
        return;
    }
    
    const timeRange = experiment.time_range || {};
    const isCurrent = experiment.is_current || false;
    
    // If experiment has a time range and is not current, use it
    if (!isCurrent && timeRange.start && timeRange.end) {
        timeRangeSelect.value = 'experiment';
        currentTimeRange = 'experiment';
        // Hide custom range inputs
        document.getElementById('customRange').style.display = 'none';
    }
}

// Load chart data for a side (A or B) with selected experiment and groups
async function loadChartData(side) {
    const experimentId = side === 'A' ? currentExperimentA : currentExperimentB;
    const selectedGroups = side === 'A' ? currentGroupsA : currentGroupsB;
    
    if (!experimentId) {
        console.error(`No experiment selected for Chart ${side}`);
        return;
    }
    
    if (!selectedGroups || selectedGroups.length === 0) {
        console.error(`No groups selected for Chart ${side}`);
        return;
    }
    
    const experiment = experiments[experimentId];
    if (!experiment) {
        console.error(`Invalid experiment: ${experimentId}`);
        return;
    }
    
    // Get devices from selected groups only
    const chartDevices = [];
    for (const groupName of selectedGroups) {
        const group = groups[groupName];
        if (group && group.devices) {
            chartDevices.push(...group.devices);
        }
    }
    
    // Remove duplicates
    const uniqueDevices = [...new Set(chartDevices)];
    
    if (uniqueDevices.length === 0) {
        alert(`No devices found in selected groups for Chart ${side}`);
        return;
    }
    
    // Determine time range
    let timeRange;
    const isCurrent = experiment.is_current || false;
    const timeRangeSelect = document.getElementById('timeRange');
    // Always use the actual dropdown value, not the cached variable
    const selectedTimeRange = timeRangeSelect ? timeRangeSelect.value : currentTimeRange;
    const useExperimentRange = selectedTimeRange === 'experiment';
    
    // Update currentTimeRange to match the dropdown
    if (selectedTimeRange !== currentTimeRange) {
        currentTimeRange = selectedTimeRange;
    }
    
    if (useExperimentRange && experiment.time_range) {
        const expTimeRange = experiment.time_range;
        if (isCurrent) {
            // Current experiment: start time to now
            timeRange = {
                start: expTimeRange.start || new Date().toISOString(),
                end: new Date().toISOString()
            };
        } else if (expTimeRange.start && expTimeRange.end) {
            // Past experiment: use its time range
            timeRange = {
                start: expTimeRange.start,
                end: expTimeRange.end
            };
        } else {
            // Fallback to selector
            timeRange = getTimeRange();
        }
    } else {
        // Use time range selector - use getTimeRange which reads from currentTimeRange
        timeRange = getTimeRange();
    }
    
    console.log(`Loading Chart ${side} with time range:`, selectedTimeRange, timeRange);
    
    try {
        const devicesParam = uniqueDevices.join(',');
        const url = `/api/data/power?devices=${encodeURIComponent(devicesParam)}&start=${encodeURIComponent(timeRange.start)}&end=${encodeURIComponent(timeRange.end)}&interval=${currentAggregation}`;
        
        // Add timeout to fetch
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minute timeout
        
        const response = await fetch(url, { signal: controller.signal });
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            let errorText = '';
            try {
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    errorText = await response.json();
                    errorText = errorText.detail || errorText.message || JSON.stringify(errorText);
                } else {
                    errorText = await response.text();
                    // If it's a short HTML error page, extract meaningful text
                    if (errorText.includes('<') && errorText.length < 500) {
                        const match = errorText.match(/<title>(.*?)<\/title>/i) || errorText.match(/>([^<]{20,200})</);
                        if (match) errorText = match[1];
                    }
                }
            } catch (e) {
                errorText = response.statusText || 'Unknown error';
            }
            
            // Provide helpful messages for common errors
            if (response.status === 502 || response.status === 504) {
                throw new Error(`Server timeout (${response.status}). Try a larger aggregation interval or shorter time range.`);
            } else if (response.status === 500) {
                throw new Error(`Server error: ${errorText}`);
            } else {
                throw new Error(`Error ${response.status}: ${errorText || response.statusText}`);
            }
        }
        
        const result = await response.json();
        
        if (result.success && result.data) {
            // If interval was auto-adjusted, update the UI
            if (result.actual_interval && result.actual_interval !== currentAggregation) {
                console.warn(`Interval auto-adjusted from ${currentAggregation} to ${result.actual_interval} for large time range`);
                currentAggregation = result.actual_interval;
                const aggSelect = document.getElementById('aggregation');
                if (aggSelect) aggSelect.value = result.actual_interval;
            }
            // Store experiment metadata with devices for later use
            const experimentWithDevices = {
                ...experiment,
                devices: uniqueDevices,
                linked_groups: selectedGroups,
                selected_groups: selectedGroups
            };
            updateChart(side, result.data, uniqueDevices, result.stats, experimentWithDevices);
        } else {
            throw new Error('Invalid response from server');
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            console.error(`Request timeout for chart ${side}`);
            alert('Request timed out. Try a shorter time range or larger aggregation interval.');
        } else {
            console.error(`Error loading chart ${side}:`, error);
            const errorMsg = error.message || 'Unknown error occurred';
            alert(`Error loading chart: ${errorMsg}`);
        }
    }
}

// Reload default chart with current time range (for time range/aggregation changes)
// Smart aggregation selection based on device count and time range
function getSmartAggregation(timeRangeHours, deviceCount, requestedAggregation) {
    // Estimate data points: (hours * 3600 / interval_seconds) * device_count
    const intervalSeconds = {
        '10s': 10, '30s': 30, '1m': 60, '5m': 300, '15m': 900, 
        '30m': 1800, '1h': 3600, '6h': 21600, '12h': 43200, '1d': 86400
    }[requestedAggregation] || 60;
    
    const estimatedPoints = (timeRangeHours * 3600 / intervalSeconds) * deviceCount;
    
    // If estimated points > 30k, auto-adjust to larger interval
    // Also adjust if: many devices (>20) with >24h range using small intervals
    if (estimatedPoints > 30000 || (timeRangeHours >= 24 && deviceCount > 20 && requestedAggregation === '1m')) {
        if (timeRangeHours > 168) { // > 7 days
            return '1h';
        } else if (timeRangeHours > 72) { // > 3 days
            return '15m';
        } else if (timeRangeHours >= 24) { // >= 1 day
            return '5m';
        } else {
            return '5m'; // Default for large device counts
        }
    }
    
    // Also handle edge case: 20+ devices with 24h+ and any small interval
    if (timeRangeHours >= 24 && deviceCount > 20 && requestedAggregation in {'10s': true, '30s': true, '1m': true, '5m': true}) {
        return '5m';
    }
    
    return requestedAggregation;
}

async function reloadDefaultChartWithCurrentTimeRange() {
    if (allDevices.length === 0 || !chartDataA || !chartDataA.experiment || chartDataA.experiment.id !== 'all-devices') {
        console.log('Cannot reload default chart - no data or not default chart');
        return;
    }
    
    const timeRange = getTimeRange();
    const timeRangeHours = (new Date(timeRange.end) - new Date(timeRange.start)) / (1000 * 60 * 60);
    
    // Auto-adjust aggregation for large queries
    const smartAggregation = getSmartAggregation(timeRangeHours, allDevices.length, currentAggregation);
    
    const devicesParam = allDevices.join(',');
    const url = `/api/data/power?devices=${encodeURIComponent(devicesParam)}&start=${encodeURIComponent(timeRange.start)}&end=${encodeURIComponent(timeRange.end)}&interval=${smartAggregation}`;
    
    if (smartAggregation !== currentAggregation) {
        console.log(`Auto-adjusted aggregation from ${currentAggregation} to ${smartAggregation} for ${timeRangeHours.toFixed(1)}h range with ${allDevices.length} devices`);
    }
    
    console.log(`Reloading default chart with time range: ${currentTimeRange}, aggregation: ${smartAggregation}`);
    
    try {
        // Add timeout to fetch
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minute timeout
        
        const response = await fetch(url, { signal: controller.signal });
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            let errorText = '';
            try {
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    errorText = await response.json();
                    errorText = errorText.detail || errorText.message || JSON.stringify(errorText);
                } else {
                    errorText = await response.text();
                    // If it's a short HTML error page, extract meaningful text
                    if (errorText.includes('<') && errorText.length < 500) {
                        const match = errorText.match(/<title>(.*?)<\/title>/i) || errorText.match(/>([^<]{20,200})</);
                        if (match) errorText = match[1];
                    }
                }
            } catch (e) {
                errorText = response.statusText || 'Unknown error';
            }
            
            // Provide helpful messages for common errors
            if (response.status === 502 || response.status === 504) {
                throw new Error(`Server timeout (${response.status}). Try a larger aggregation interval or shorter time range.`);
            } else if (response.status === 500) {
                throw new Error(`Server error: ${errorText}`);
            } else {
                throw new Error(`Error ${response.status}: ${errorText || response.statusText}`);
            }
        }
        
        const result = await response.json();
        
        if (result.success && result.data) {
            // If interval was auto-adjusted, update the UI
            if (result.actual_interval && result.actual_interval !== currentAggregation) {
                console.warn(`Interval auto-adjusted from ${currentAggregation} to ${result.actual_interval} for large time range`);
                currentAggregation = result.actual_interval;
                const aggSelect = document.getElementById('aggregation');
                if (aggSelect) aggSelect.value = result.actual_interval;
            }
            // Update chart with new data using the existing experiment object
            updateChart('A', result.data, allDevices, result.stats, chartDataA.experiment);
            console.log(`Default chart reloaded with ${currentTimeRange} time range and ${currentAggregation} aggregation`);
        } else {
            console.error('Failed to reload default chart:', result);
            throw new Error('Invalid response from server');
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            console.error('Request timeout after 5 minutes');
            alert('Request timed out. Try a shorter time range or larger aggregation interval.');
        } else {
            console.error('Error reloading default chart:', error);
            const errorMsg = error.message || 'Unknown error occurred';
            // Only show alert for manual reloads, not auto-refresh
            // Check if this is being called from auto-refresh by checking call stack
            const isAutoRefresh = new Error().stack?.includes('refreshCurrentCharts') || 
                                   new Error().stack?.includes('setInterval');
            if (!isAutoRefresh) {
                alert(`Error reloading chart: ${errorMsg}`);
            } else {
                console.warn('Auto-refresh error (silent):', errorMsg);
            }
        }
    }
}

// Load default chart with all devices (last hour)
async function loadDefaultChart() {
    if (allDevices.length === 0) {
        console.log('No devices available for default chart');
        return;
    }
    
    // Only set to 1h if this is the initial load (time range not manually selected)
    const timeRangeSelect = document.getElementById('timeRange');
    if (timeRangeSelect && (!timeRangeSelect.value || timeRangeSelect.value === '1h')) {
        currentTimeRange = '1h';
        if (timeRangeSelect) {
            timeRangeSelect.value = '1h';
        }
    }
    
    const selectedTimeRange = timeRangeSelect ? timeRangeSelect.value : currentTimeRange;
    console.log(`Loading default chart with ${allDevices.length} devices for ${selectedTimeRange}...`);
    
    // Create a default experiment-like object for all devices
    const defaultExperiment = {
        id: 'all-devices',
        name: 'All Devices',
        description: 'Default view showing all devices',
        time_range: null,
        is_current: false,
        devices: allDevices,
        linked_groups: [],
        selected_groups: []
    };
    
    // Get time range (will use current selection)
    const timeRange = getTimeRange();
    
    try {
        const devicesParam = allDevices.join(',');
        const url = `/api/data/power?devices=${encodeURIComponent(devicesParam)}&start=${encodeURIComponent(timeRange.start)}&end=${encodeURIComponent(timeRange.end)}&interval=${currentAggregation}`;
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.success && result.data) {
            // Update chart A with all devices
            updateChart('A', result.data, allDevices, result.stats, defaultExperiment);
            console.log('Default chart loaded successfully');
        }
    } catch (error) {
        console.error('Error loading default chart:', error);
    }
}

// Initialize charts
function initializeCharts() {
    const canvasA = document.getElementById('chartA');
    const canvasB = document.getElementById('chartB');
    
    if (!canvasA || !canvasB) {
        console.error('Chart canvas elements not found');
        return;
    }
    
    const ctxA = canvasA.getContext('2d');
    const ctxB = canvasB.getContext('2d');
    
    if (!ctxA || !ctxB) {
        console.error('Failed to get 2D context from canvas elements');
        return;
    }
    
    const chartConfig = {
        type: 'line',
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'nearest',
                intersect: true,
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    onClick: function(e, legendItem, legend) {
                        const index = legendItem.datasetIndex;
                        const chart = legend.chart;
                        const dataset = chart.data.datasets[index];
                        
                        // Don't allow toggling statistical overlays - only device datasets
                        const isStatOverlay = ['Mean', 'Median', 'Total', 'Average', 'Annotations'].some(stat => 
                            dataset.label.includes(stat) || dataset.label.startsWith(stat + ':')
                        );
                        
                        if (isStatOverlay) {
                            return; // Prevent toggling statistical overlays
                        }
                        
                        // Grafana-like behavior: shift+click = toggle, single click = select only
                        const isShiftPressed = e.native?.shiftKey || e.shiftKey;
                        
                        if (isShiftPressed) {
                            // Shift+click: Toggle this device only (add/remove from selection)
                            const meta = chart.getDatasetMeta(index);
                            meta.hidden = meta.hidden === null ? !dataset.hidden : null;
                        } else {
                            // Single click: Show only this device (hide all other device datasets)
                            // Find all device datasets (exclude statistical overlays)
                            const deviceDatasets = chart.data.datasets
                                .map((ds, idx) => ({ dataset: ds, index: idx }))
                                .filter(({ dataset }) => {
                                    const label = dataset.label || '';
                                    return !['Mean', 'Median', 'Total', 'Average', 'Annotations'].some(stat => 
                                        label.includes(stat) || label.startsWith(stat + ':')
                                    );
                                });
                            
                            // Hide all device datasets except the clicked one
                            deviceDatasets.forEach(({ index: idx }) => {
                                const meta = chart.getDatasetMeta(idx);
                                meta.hidden = (idx !== index); // Hide if not the clicked one
                            });
                        }
                        
    chart.update();
    
    // Update scrollbar if chart is zoomed
    const chartId = chart === chartA ? 'A' : 'B';
    updateChartScrollbar(chartId);
    
    // Recalculate statistics based on visible devices after toggle
    setTimeout(() => recalculateStatisticsForChart(chart), 100);
                    }
                },
                tooltip: {
                    mode: 'nearest',
                    intersect: false,
                    callbacks: {
                        title: function(context) {
                            // Show timestamp
                            if (context && context.length > 0) {
                                return context[0].label;
                            }
                            return '';
                        },
                        label: function(context) {
                            // Show only the hovered line's label and value
                            const label = context.dataset.label || '';
                            const value = context.parsed.y !== null && context.parsed.y !== undefined ? context.parsed.y.toFixed(1) + ' W' : 'N/A';
                            return `${label}: ${value}`;
                        }
                    },
                    filter: function(tooltipItems) {
                        // Only show the first/closest tooltip item (the one actually being hovered)
                        if (tooltipItems && tooltipItems.length > 0) {
                            return [tooltipItems[0]];
                        }
                        return tooltipItems;
                    }
                },
                annotation: {
                    annotations: {}
                },
                zoom: {
                    zoom: {
                        wheel: {
                            enabled: true,
                            speed: 0.1, // Slower zoom for better control
                        },
                        pinch: {
                            enabled: true
                        },
                        mode: 'x',
                        // Enable zoom out with shift+wheel or right-click drag
                        drag: {
                            enabled: false // Disable drag zoom, use pan instead
                        }
                    },
                    pan: {
                        enabled: true,
                        mode: 'xy', // Pan both horizontally and vertically
                        threshold: 10, // Minimum pixels to move before panning starts
                        modifierKey: null, // No modifier key needed for pan
                        speed: 10, // Pan speed multiplier
                    },
                    limits: {
                        x: {min: 'original', max: 'original'}
                    },
                    onZoom: function({chart}) {
                        if (chart === chartA && chartDataA) {
                            updateStatsForVisibleRange(chartA, 'A', chartDataA.data, chartDataA.devices);
                            setTimeout(() => updateChartScrollbar('A'), 100);
                        } else if (chart === chartB && chartDataB) {
                            updateStatsForVisibleRange(chartB, 'B', chartDataB.data, chartDataB.devices);
                            setTimeout(() => updateChartScrollbar('B'), 100);
                        }
                    },
                    onPan: function({chart}) {
                        if (chart === chartA && chartDataA) {
                            updateStatsForVisibleRange(chartA, 'A', chartDataA.data, chartDataA.devices);
                            setTimeout(() => updateChartScrollbar('A'), 100);
                        } else if (chart === chartB && chartDataB) {
                            updateStatsForVisibleRange(chartB, 'B', chartDataB.data, chartDataB.devices);
                            setTimeout(() => updateChartScrollbar('B'), 100);
                        }
                    },
                    onZoomComplete: function({chart}) {
                        if (chart === chartA) {
                            setTimeout(() => updateChartScrollbar('A'), 150);
                        } else if (chart === chartB) {
                            setTimeout(() => updateChartScrollbar('B'), 150);
                        }
                    },
                    onPanComplete: function({chart}) {
                        // Pan complete handler
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        tooltipFormat: 'PPpp',
                        displayFormats: {
                            minute: 'HH:mm',
                            hour: 'HH:mm'
                        }
                    },
                    title: {
                        display: true,
                        text: 'Time'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Power (W)'
                    },
                    beginAtZero: true
                }
            },
            elements: {
                line: {
                    borderJoinStyle: 'round',
                    borderCapStyle: 'round'
                },
                point: {
                    radius: 0,
                    hoverRadius: 4
                }
            }
        }
    };
    
    chartA = new Chart(ctxA, { ...chartConfig, data: { datasets: [] } });
    chartB = new Chart(ctxB, { ...chartConfig, data: { datasets: [] } });
    
    // Move scrollbar container to correct position (after chart, before legend)
    // Chart.js might render legend after our HTML, so we reposition the scrollbar
    moveScrollbarToCorrectPosition('A');
    moveScrollbarToCorrectPosition('B');
    
    // Add click handlers for annotation markers
    setupAnnotationClickHandlers(chartA);
    setupAnnotationClickHandlers(chartB);
    
    // Setup scrollbar handlers
    setupChartScrollbars();
    
    // Start polling to detect zoom/pan changes (fallback if callbacks don't fire)
    startScrollbarPolling();
    
    // Note: Zoom/pan stats updates are handled by the zoom plugin callbacks
    // which are configured in the chart options if needed
}

// Poll for zoom/pan changes (fallback if zoom plugin callbacks don't fire)
function startScrollbarPolling() {
    if (scrollbarUpdateInterval) {
        clearInterval(scrollbarUpdateInterval);
    }
    
    scrollbarUpdateInterval = setInterval(() => {
        // Check Chart A
        if (chartA && chartDataA) {
            const xScale = chartA.scales?.x;
            if (xScale) {
                const currentMin = typeof xScale.min === 'number' ? xScale.min : (xScale.min instanceof Date ? xScale.min.getTime() : new Date(xScale.min).getTime());
                const currentMax = typeof xScale.max === 'number' ? xScale.max : (xScale.max instanceof Date ? xScale.max.getTime() : new Date(xScale.max).getTime());
                
                // Check if scale values changed
                if (lastScaleValuesA.min !== currentMin || lastScaleValuesA.max !== currentMax) {
                    lastScaleValuesA.min = currentMin;
                    lastScaleValuesA.max = currentMax;
                    updateChartScrollbar('A');
                }
            }
        }
        
        // Check Chart B
        if (chartB && chartDataB) {
            const xScale = chartB.scales?.x;
            if (xScale) {
                const currentMin = typeof xScale.min === 'number' ? xScale.min : (xScale.min instanceof Date ? xScale.min.getTime() : new Date(xScale.min).getTime());
                const currentMax = typeof xScale.max === 'number' ? xScale.max : (xScale.max instanceof Date ? xScale.max.getTime() : new Date(xScale.max).getTime());
                
                // Check if scale values changed
                if (lastScaleValuesB.min !== currentMin || lastScaleValuesB.max !== currentMax) {
                    lastScaleValuesB.min = currentMin;
                    lastScaleValuesB.max = currentMax;
                    updateChartScrollbar('B');
                }
            }
        }
    }, 200); // Check every 200ms
}

function stopScrollbarPolling() {
    if (scrollbarUpdateInterval) {
        clearInterval(scrollbarUpdateInterval);
        scrollbarUpdateInterval = null;
    }
}

// Track previous scale values to detect zoom/pan changes
let lastScaleValuesA = { min: null, max: null };
let lastScaleValuesB = { min: null, max: null };
let scrollbarUpdateInterval = null;

// Move scrollbar container to correct position (after chart wrapper, before legend)
function moveScrollbarToCorrectPosition(chartId) {
    const chartContainer = chartId === 'A' 
        ? document.getElementById('chartContainerA')
        : document.getElementById('chartContainerB');
    const chartWrapper = chartContainer?.querySelector('.chart-wrapper');
    const scrollbarContainer = chartId === 'A'
        ? document.getElementById('scrollbarContainerA')
        : document.getElementById('scrollbarContainerB');
    
    if (chartContainer && chartWrapper && scrollbarContainer) {
        // Insert scrollbar container right after chart wrapper
        chartWrapper.parentNode.insertBefore(scrollbarContainer, chartWrapper.nextSibling);
    }
}

// Setup scrollbar controls for chart navigation
function setupChartScrollbars() {
    const scrollbarA = document.getElementById('chartAScrollbar');
    const scrollbarB = document.getElementById('chartBScrollbar');
    
    if (scrollbarA) {
        scrollbarA.addEventListener('input', function(e) {
            handleScrollbarChange('A', parseFloat(e.target.value));
        });
    }
    
    if (scrollbarB) {
        scrollbarB.addEventListener('input', function(e) {
            handleScrollbarChange('B', parseFloat(e.target.value));
        });
    }
}

// Handle scrollbar changes - pan the chart horizontally
function handleScrollbarChange(chartId, scrollValue) {
    const chart = chartId === 'A' ? chartA : chartB;
    if (!chart) return;
    
    // Prevent scrollbar from being hidden during interaction
    const container = chartId === 'A' ? document.getElementById('scrollbarContainerA') : document.getElementById('scrollbarContainerB');
    if (container) {
        container.style.display = 'block'; // Force visible during interaction
    }
    
    const zoomPlugin = chart.options.plugins.zoom;
    if (!zoomPlugin || !chart.isDatasetVisible) return;
    
    // Get the current scale limits
    const xScale = chart.scales.x;
    if (!xScale) return;
    
    // Get the data range
    const data = chartId === 'A' ? chartDataA : chartDataB;
    if (!data || !data.data || data.data.length === 0) return;
    
    const timestamps = data.data.map(d => new Date(d.timestamp).getTime()).filter(t => !isNaN(t));
    if (timestamps.length === 0) return;
    
    const minTime = Math.min(...timestamps);
    const maxTime = Math.max(...timestamps);
    const timeRange = maxTime - minTime;
    
    // Get current visible range
    const currentMin = xScale.min;
    const currentMax = xScale.max;
    const currentRange = currentMax - currentMin;
    
    // Calculate new position based on scroll value (0-100)
    const scrollPosition = scrollValue / 100;
    const availableScroll = timeRange - currentRange;
    
    if (availableScroll <= 0) {
        // Chart is not zoomed in, hide scrollbar
        const container = chartId === 'A' ? document.getElementById('scrollbarContainerA') : document.getElementById('scrollbarContainerB');
        if (container) container.style.display = 'none';
        return;
    }
    
    const newMin = minTime + (scrollPosition * availableScroll);
    const newMax = newMin + currentRange;
    
    // Update the chart's x-axis scale
    xScale.options.min = new Date(newMin);
    xScale.options.max = new Date(newMax);
    chart.update('none'); // Update without animation
    
    // Update scrollbar labels
    updateScrollbarLabels(chartId, new Date(newMin), new Date(newMax));
    
    // Re-update scrollbar position to prevent hiding
    setTimeout(() => {
        updateChartScrollbar(chartId);
    }, 50);
}

// Update scrollbar labels with time range
function updateScrollbarLabels(chartId, minDate, maxDate) {
    const minLabel = chartId === 'A' ? document.getElementById('scrollbarMinA') : document.getElementById('scrollbarMinB');
    const maxLabel = chartId === 'A' ? document.getElementById('scrollbarMaxA') : document.getElementById('scrollbarMaxB');
    
    if (minLabel) {
        minLabel.textContent = minDate.toLocaleString();
    }
    if (maxLabel) {
        maxLabel.textContent = maxDate.toLocaleString();
    }
}

// Update scrollbar position and visibility when chart zoom changes
function updateChartScrollbar(chartId) {
    const chart = chartId === 'A' ? chartA : chartB;
    const data = chartId === 'A' ? chartDataA : chartDataB;
    const scrollbar = chartId === 'A' ? document.getElementById('chartAScrollbar') : document.getElementById('chartBScrollbar');
    const container = chartId === 'A' ? document.getElementById('scrollbarContainerA') : document.getElementById('scrollbarContainerB');
    
    if (!chart || !data || !data.data || !scrollbar || !container) {
        if (container) container.style.display = 'none';
        return;
    }
    
    const xScale = chart.scales.x;
    if (!xScale) return;
    
    const timestamps = data.data.map(d => new Date(d.timestamp).getTime()).filter(t => !isNaN(t));
    if (timestamps.length === 0) {
        container.style.display = 'none';
        return;
    }
    
    const minTime = Math.min(...timestamps);
    const maxTime = Math.max(...timestamps);
    const timeRange = maxTime - minTime;
    
    // Get current visible range - handle both Date objects and string timestamps
    let currentMin, currentMax;
    try {
        // Read the actual displayed range from the scale
        // Chart.js zoom plugin stores zoomed limits in xScale.min/max, but we need to get the actual pixel range
        // The scale.min and scale.max represent the data range, but after zoom they represent the visible range
        if (xScale.min instanceof Date) {
            currentMin = xScale.min.getTime();
        } else if (typeof xScale.min === 'string') {
            currentMin = new Date(xScale.min).getTime();
        } else if (typeof xScale.min === 'number') {
            currentMin = xScale.min;
        } else {
            // Try to parse as number or date
            currentMin = new Date(xScale.min).getTime();
        }
        
        if (xScale.max instanceof Date) {
            currentMax = xScale.max.getTime();
        } else if (typeof xScale.max === 'string') {
            currentMax = new Date(xScale.max).getTime();
        } else if (typeof xScale.max === 'number') {
            currentMax = xScale.max;
        } else {
            // Try to parse as number or date
            currentMax = new Date(xScale.max).getTime();
        }
    } catch (e) {
        console.error(`Error parsing scale values for ${chartId}:`, e);
        container.style.display = 'none';
        return;
    }
    
    const currentRange = currentMax - currentMin;
    
    // Show scrollbar if zoomed in (current range is less than 99% of total range)
    // Use a very lenient threshold - if showing less than 99% of the range, show scrollbar
    const zoomRatio = timeRange > 0 ? (currentRange / timeRange) : 1;
    // Calculate if zoomed - use a small buffer (1% = 36000ms for 1 hour) to account for rounding
    const buffer = Math.max(1000, timeRange * 0.01); // At least 1 second, or 1% of range
    const isZoomed = timeRange > 0 && (currentRange + buffer) < timeRange;
    
    
    if (isZoomed) {
        container.style.display = 'block';
        container.style.visibility = 'visible';
        container.style.opacity = '1';
        
        // Calculate scrollbar position
        const availableScroll = timeRange - currentRange;
        if (availableScroll > 0) {
            const scrollPosition = ((currentMin - minTime) / availableScroll) * 100;
            scrollbar.value = Math.max(0, Math.min(100, scrollPosition));
        } else {
            scrollbar.value = 0;
        }
        
        // Update labels
        updateScrollbarLabels(chartId, new Date(currentMin), new Date(currentMax));
    } else {
        container.style.display = 'none';
        container.style.visibility = 'hidden';
    }
}

// Setup click handlers for annotation markers
function setupAnnotationClickHandlers(chart) {
    if (!chart) return;
    
    const canvas = chart.canvas;
    canvas.addEventListener('click', (e) => {
        const points = chart.getElementsAtEventForMode(e, 'nearest', { intersect: true }, true);
        if (points.length > 0) {
            const point = points[0];
            const dataset = chart.data.datasets[point.datasetIndex];
            
            // Check if this is an annotation marker
            if (dataset.label === 'Annotations' && dataset.data[point.index]) {
                const dataPoint = dataset.data[point.index];
                if (dataPoint.annotationId && dataPoint.annotation) {
                    const rect = canvas.getBoundingClientRect();
                    showAnnotationPopup(dataPoint.annotation, e.clientX, e.clientY);
                }
            }
        }
    });
    
    // Change cursor when hovering over annotation markers
    canvas.addEventListener('mousemove', (e) => {
        const points = chart.getElementsAtEventForMode(e, 'nearest', { intersect: true }, true);
        if (points.length > 0) {
            const point = points[0];
            const dataset = chart.data.datasets[point.datasetIndex];
            if (dataset.label === 'Annotations') {
                canvas.style.cursor = 'pointer';
            } else {
                canvas.style.cursor = 'default';
            }
        } else {
            canvas.style.cursor = 'default';
        }
    });
}

// Update chart
function updateChart(side, data, devices, stats, experiment) {
    const chart = side === 'A' ? chartA : chartB;
    const titleEl = document.getElementById(`chart${side}Title`);
    const totalEl = document.getElementById(`total${side}`);
    const avgEl = document.getElementById(`avg${side}`);
    const meanEl = document.getElementById(`mean${side}`);
    const medianEl = document.getElementById(`median${side}`);
    
    if (!chart) {
        console.error(`Chart ${side} does not exist`);
        return;
    }
    
    console.log(`updateChart(${side}):`, {
        dataPoints: data?.length || 0,
        devices: devices?.length || 0,
        hasStats: !!stats
    });
    
    // Store chart data for recalculation
    if (side === 'A') {
        chartDataA = { data, devices, stats, experiment };
    } else {
        chartDataB = { data, devices, stats, experiment };
    }
    
    // Update title with experiment status indicator
    const exp = typeof experiment === 'object' ? experiment : experiments[experiment] || {};
    const isCurrent = exp.is_current || false;
    const statusIndicator = isCurrent ? ' 🔵 ' : '';
    titleEl.textContent = `${statusIndicator}${exp.name || experiment || 'Chart ' + side} - Power Consumption`;
    
    // Update stats for the full dataset initially
    if (stats) {
        const totalEl = document.getElementById(`total${side}`);
        const avgEl = document.getElementById(`avg${side}`);
        const meanEl = document.getElementById(`mean${side}`);
        const medianEl = document.getElementById(`median${side}`);
        
        totalEl.textContent = stats.total_kwh ? stats.total_kwh.toFixed(2) : '0';
        avgEl.textContent = stats.average_watts ? stats.average_watts.toFixed(1) : '0';
        meanEl.textContent = stats.mean_watts ? stats.mean_watts.toFixed(1) : '0';
        medianEl.textContent = stats.median_watts ? stats.median_watts.toFixed(1) : '0';
    }
    
    // Prepare datasets
    const datasets = [];
    
    // Get curve configuration
    const curveConfig = getCurveConfig();
    
    // Device datasets (only if showDevices is true)
    if (showDevices) {
        devices.forEach((device, index) => {
            // Filter out null/undefined values but keep zeros (zeros are valid data)
            const deviceData = data
                .map(point => ({
                    x: point.timestamp,
                    y: point[device] !== null && point[device] !== undefined ? point[device] : null
                }))
                .filter(point => point.y !== null && point.y !== undefined);
            
            datasets.push({
                label: device,
                data: deviceData,
                borderColor: deviceColors[index % deviceColors.length],
                backgroundColor: deviceColors[index % deviceColors.length] + '20',
                borderWidth: 2,
                pointRadius: 0,
                ...curveConfig
            });
        });
    }
    
    // Statistical overlays
    if (showMean && stats && stats.mean_watts) {
        datasets.push({
            label: 'Mean',
            data: data.map(p => ({ x: p.timestamp, y: stats.mean_watts })),
            borderColor: 'red',
            borderWidth: 3,
            borderDash: [5, 5],
            pointRadius: 0,
            fill: false,
            ...curveConfig
        });
    }
    
    if (showMedian && stats && stats.median_watts) {
        datasets.push({
            label: 'Median',
            data: data.map(p => ({ x: p.timestamp, y: stats.median_watts })),
            borderColor: 'orange',
            borderWidth: 3,
            borderDash: [10, 5],
            pointRadius: 0,
            fill: false,
            ...curveConfig
        });
    }
    
    // Total (sum of all devices)
    if (showTotal && data.length > 0) {
        // Forward-fill missing values: track last known value for each device
        const lastKnownValues = {};
        devices.forEach(dev => { lastKnownValues[dev] = null; });
        
        // First pass: forward-fill missing values
        const filledData = data.map(point => {
            const filledPoint = { ...point };
            devices.forEach(dev => {
                if (filledPoint[dev] !== null && filledPoint[dev] !== undefined && !isNaN(filledPoint[dev])) {
                    // Update last known value
                    lastKnownValues[dev] = filledPoint[dev];
                } else if (lastKnownValues[dev] !== null) {
                    // Forward-fill with last known value
                    filledPoint[dev] = lastKnownValues[dev];
                }
            });
            return filledPoint;
        });
        
        const totalData = filledData
            .map(point => {
                const sum = devices.reduce((acc, dev) => {
                    const val = point[dev];
                    return acc + (val !== null && val !== undefined && !isNaN(val) ? val : 0);
                }, 0);
                return { x: point.timestamp, y: sum > 0 ? sum : null };
            })
            .filter(point => point.y !== null);
        
        datasets.push({
            label: 'Total (Sum)',
            data: totalData,
            borderColor: 'purple',
            borderWidth: 3,
            pointRadius: 0,
            fill: false,
            ...curveConfig
        });
    }
    
    // Average (average of selected devices in the group only)
    if (showAverage && data.length > 0 && devices.length > 0) {
        // Create a set of valid devices from the selected group that actually have data
        const validDevices = devices.filter(dev => {
            // Device must be in the selected group AND have at least some data points
            const hasData = data.some(point => {
                const value = point[dev];
                return value !== null && value !== undefined && !isNaN(value) && value > 0;
            });
            return hasData;
        });
        
        if (validDevices.length > 0) {
            const avgData = data
                .map(point => {
                    // Get values only from devices in the selected group
                    const values = validDevices
                        .map(dev => {
                            const val = point[dev];
                            // Only include valid numeric values
                            if (val === null || val === undefined || isNaN(val)) return null;
                            return parseFloat(val);
                        })
                        .filter(v => v !== null && !isNaN(v));
                    
                    // Only calculate average if we have at least one valid value
                    if (values.length === 0) return null;
                    
                    const avg = values.reduce((a, b) => a + b, 0) / values.length;
                    return { x: point.timestamp, y: avg };
                })
                .filter(point => point !== null && point.y !== null && !isNaN(point.y));
            
            datasets.push({
                label: `Average (${validDevices.length} device${validDevices.length !== 1 ? 's' : ''} in group)`,
                data: avgData,
                borderColor: 'blue',
                borderWidth: 3,
                borderDash: [15, 5],
                pointRadius: 0,
                fill: false,
                ...curveConfig
            });
        }
    }
    
    // Clear existing datasets completely
    chart.data.datasets = [];
    chart.update('none'); // Clear first
    
    // Set new datasets
    chart.data.datasets = datasets;
    
    // Add annotation markers for this experiment (as dots below timeline)
    addAnnotationMarkers(chart, experiment.name || experiment.id || experiment, data);
    
    // Force complete chart update
    chart.update('none');
    
    // Store chart data for legend-based recalculation
    if (side === 'A') {
        chartDataA = { data, devices, stats, experiment };
    } else {
        chartDataB = { data, devices, stats, experiment };
    }
    
    // Update scrollbar visibility and position after chart update
    setTimeout(() => {
        try {
            if (typeof updateChartScrollbar === 'function') {
                updateChartScrollbar(side);
            }
        } catch (e) {
            // Silently fail - scrollbar update is non-critical
        }
    }, 300);
}

// Recalculate statistics based on visible device datasets
function recalculateStatisticsForChart(chart) {
    // Determine which chart this is
    const isChartA = chart === chartA;
    const chartData = isChartA ? chartDataA : chartDataB;
    
    if (!chartData) return;
    
    const { data, devices, stats, experiment } = chartData;
    
    // Get visible device datasets (exclude statistical overlays and annotations)
    const visibleDevices = [];
    chart.data.datasets.forEach((dataset, index) => {
        const meta = chart.getDatasetMeta(index);
        const isHidden = meta.hidden;
        
        // Check if this is a device dataset (not a statistical overlay or annotation)
        const isDeviceDataset = devices.includes(dataset.label);
        const isStatOverlay = ['Mean', 'Median', 'Total (Sum)', 'Average'].some(stat => 
            dataset.label.includes(stat) || dataset.label.startsWith(stat)
        );
        const isAnnotation = dataset.label === 'Annotations';
        
        if (isDeviceDataset && !isHidden && !isStatOverlay && !isAnnotation) {
            visibleDevices.push(dataset.label);
        }
    });
    
    if (visibleDevices.length === 0) {
        // No visible devices, hide all statistical overlays
        updateStatisticalOverlays(chart, [], data, devices, isChartA ? 'A' : 'B');
        return;
    }
    
    // Recalculate statistics based on visible devices only
    updateStatisticalOverlays(chart, visibleDevices, data, devices, isChartA ? 'A' : 'B');
}

// Update statistical overlay datasets based on visible devices
function updateStatisticalOverlays(chart, visibleDevices, data, allDevices, side) {
    const curveConfig = getCurveConfig();
    const datasets = chart.data.datasets;
    
    // Identify which datasets are statistical overlays (not devices or annotations)
    const statLabels = ['Mean', 'Median', 'Total', 'Average'];
    const indicesToRemove = [];
    let deviceDatasetCount = 0;
    let annotationIndex = -1;
    
    datasets.forEach((dataset, index) => {
        const isDevice = visibleDevices.includes(dataset.label) || allDevices.includes(dataset.label);
        const isStat = statLabels.some(label => 
            dataset.label.includes(label) || dataset.label.startsWith(side + ': ' + label)
        );
        const isAnnotation = dataset.label === 'Annotations';
        
        if (isDevice && !isStat && !isAnnotation) {
            deviceDatasetCount++;
        } else if (isStat) {
            indicesToRemove.push(index);
        } else if (isAnnotation) {
            annotationIndex = index;
        }
    });
    
    // Remove statistical overlay datasets (in reverse order to maintain indices)
    indicesToRemove.reverse().forEach(index => {
        datasets.splice(index, 1);
        if (annotationIndex > index) annotationIndex--;
    });
    
    // Recalculate statistics based on visible devices
    if (visibleDevices.length > 0) {
        // Calculate values at each timestamp for visible devices only
        const allValues = data.map(point => {
            const values = visibleDevices
                .map(dev => {
                    const val = point[dev];
                    if (val === null || val === undefined || isNaN(val)) return null;
                    return parseFloat(val);
                })
                .filter(v => v !== null && !isNaN(v));
            return { timestamp: point.timestamp, values };
        });
        
        // Find insertion point (after device datasets, before annotations)
        let insertIndex = deviceDatasetCount;
        if (annotationIndex >= 0 && annotationIndex > insertIndex) {
            insertIndex = annotationIndex;
        }
        
        const newStatDatasets = [];
        
        // Mean
        if (showMean) {
            const meanData = allValues.map(item => {
                if (item.values.length === 0) return null;
                const mean = item.values.reduce((a, b) => a + b, 0) / item.values.length;
                return { x: item.timestamp, y: mean };
            }).filter(p => p !== null);
            
            newStatDatasets.push({
                label: side ? `${side}: Mean` : 'Mean',
                data: meanData,
                borderColor: side === 'A' ? '#e74c3c' : (side === 'B' ? '#c0392b' : 'red'),
                borderWidth: 3,
                borderDash: [5, 5],
                pointRadius: 0,
                fill: false,
                ...curveConfig
            });
        }
        
        // Median
        if (showMedian) {
            const medianData = allValues.map(item => {
                if (item.values.length === 0) return null;
                const sorted = [...item.values].sort((a, b) => a - b);
                const mid = Math.floor(sorted.length / 2);
                const median = sorted.length % 2 === 0 
                    ? (sorted[mid - 1] + sorted[mid]) / 2 
                    : sorted[mid];
                return { x: item.timestamp, y: median };
            }).filter(p => p !== null);
            
            newStatDatasets.push({
                label: side ? `${side}: Median` : 'Median',
                data: medianData,
                borderColor: side === 'A' ? '#e67e22' : (side === 'B' ? '#d35400' : 'orange'),
                borderWidth: 3,
                borderDash: [10, 5],
                pointRadius: 0,
                fill: false,
                ...curveConfig
            });
        }
        
        // Total (Sum) - exclude zeros and nulls to prevent wavy lines
        if (showTotal) {
            // Calculate totals, excluding zeros and nulls for smoother lines
            const totalData = allValues.map(item => {
                // Filter out null, undefined, NaN, and zero values
                const validValues = item.values.filter(v => 
                    v !== null && 
                    v !== undefined && 
                    !isNaN(v) && 
                    v > 0 // Exclude zeros to prevent wavy behavior
                );
                if (validValues.length === 0) return null;
                const sum = validValues.reduce((a, b) => a + b, 0);
                return sum > 0 ? { x: item.timestamp, y: sum } : null;
            }).filter(p => p !== null && p.y !== null && p.y > 0);
            
            // Forward-fill gaps to smooth out the line (prevent wavy pattern)
            let lastKnownTotal = null;
            const smoothedTotalData = totalData.map((point, index) => {
                if (point && point.y !== null && point.y > 0) {
                    lastKnownTotal = point.y;
                    return point;
                } else if (lastKnownTotal !== null) {
                    // Forward-fill with last known value
                    return { x: point.x, y: lastKnownTotal };
                }
                return null;
            }).filter(p => p !== null && p.y !== null && p.y > 0);
            
            if (smoothedTotalData.length > 0) {
                newStatDatasets.push({
                    label: side ? `${side}: Total` : 'Total (Sum)',
                    data: smoothedTotalData,
                    borderColor: side === 'A' ? '#9b59b6' : (side === 'B' ? '#8e44ad' : 'purple'),
                    borderWidth: 3,
                    pointRadius: 0,
                    fill: false,
                    ...curveConfig
                });
            }
        }
        
        // Average
        if (showAverage) {
            const avgData = allValues.map(item => {
                if (item.values.length === 0) return null;
                const avg = item.values.reduce((a, b) => a + b, 0) / item.values.length;
                return { x: item.timestamp, y: avg };
            }).filter(p => p !== null);
            
            newStatDatasets.push({
                label: side ? `${side}: Average (${visibleDevices.length} device${visibleDevices.length !== 1 ? 's' : ''})` : `Average (${visibleDevices.length} device${visibleDevices.length !== 1 ? 's' : ''})`,
                data: avgData,
                borderColor: side === 'A' ? '#3498db' : (side === 'B' ? '#2980b9' : 'blue'),
                borderWidth: 3,
                borderDash: [15, 5],
                pointRadius: 0,
                fill: false,
                ...curveConfig
            });
        }
        
        // Insert new statistical datasets at the correct position
        newStatDatasets.forEach((dataset, idx) => {
            datasets.splice(insertIndex + idx, 0, dataset);
        });
    }
    
    chart.update();
}

// Add annotation markers to chart as dots below the timeline
function addAnnotationMarkers(chart, experimentId, dataPoints) {
    if (!experimentId || !annotations) return;
    
    // Get annotations for this experiment
    const experimentAnnotations = Object.values(annotations).filter(ann => ann.experiment_id === experimentId);
    
    if (experimentAnnotations.length === 0) return;
    
    // Get time range from chart data to filter annotations
    if (!dataPoints || dataPoints.length === 0) return;
    
    const timeRange = {
        start: new Date(dataPoints[0].timestamp),
        end: new Date(dataPoints[dataPoints.length - 1].timestamp)
    };
    
    // Filter annotations within the visible time range
    const visibleAnnotations = experimentAnnotations.filter(ann => {
        const annTime = new Date(ann.timestamp);
        return annTime >= timeRange.start && annTime <= timeRange.end;
    });
    
    if (visibleAnnotations.length === 0) return;
    
    // Create annotation markers dataset - place dots at y = 0 (at the bottom of the chart)
    const annotationData = visibleAnnotations.map(ann => {
        const timestamp = new Date(ann.timestamp);
        return {
            x: timestamp.toISOString(),
            y: 0, // Place at bottom of chart (y=0)
            annotationId: ann.id,
            annotation: ann
        };
    });
    
    // Add annotation markers dataset
    chart.data.datasets.push({
        label: 'Annotations',
        data: annotationData,
        type: 'scatter',
        pointRadius: 8,
        pointHoverRadius: 10,
        pointBackgroundColor: annotationData.map(d => d.annotation.color || '#007bff'),
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointStyle: 'circle',
        showLine: false,
        order: 1000, // Ensure annotations are on top
        yAxisID: 'y' // Use the same y-axis
    });
}

// Show annotation popup when clicking on marker
function showAnnotationPopup(annotation, x, y) {
    // Remove existing popup if any
    const existingPopup = document.getElementById('annotation-popup');
    if (existingPopup) {
        existingPopup.remove();
    }
    
    // Create popup element
    const popup = document.createElement('div');
    popup.id = 'annotation-popup';
    popup.style.cssText = `
        position: fixed;
        left: ${x + 10}px;
        top: ${y + 10}px;
        background: white;
        border: 2px solid ${annotation.color || '#007bff'};
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 10000;
        max-width: 300px;
        font-size: 0.9rem;
    `;
    
    const annTime = new Date(annotation.timestamp);
    popup.innerHTML = `
        <div style="margin-bottom: 10px;">
            <strong style="color: ${annotation.color || '#007bff'};">${annotation.label || 'Untitled'}</strong>
        </div>
        ${annotation.description ? `<div style="margin-bottom: 10px; color: #666;">${annotation.description}</div>` : ''}
        <div style="color: #999; font-size: 0.85rem;">
            ${annTime.toLocaleString()}
        </div>
        <button onclick="this.parentElement.remove()" style="position: absolute; top: 5px; right: 5px; background: none; border: none; font-size: 20px; cursor: pointer; color: #999;">&times;</button>
    `;
    
    document.body.appendChild(popup);
    
    // Close popup when clicking outside or after 10 seconds
    setTimeout(() => {
        if (popup.parentElement) {
            popup.remove();
        }
    }, 10000);
    
    document.addEventListener('click', function closePopup(e) {
        if (!popup.contains(e.target)) {
            popup.remove();
            document.removeEventListener('click', closePopup);
        }
    }, { once: true });
}

// Update charts (for toggles)
function updateCharts() {
    console.log('updateCharts called - showMean:', showMean, 'showMedian:', showMedian, 'showTotal:', showTotal, 'showAverage:', showAverage, 'splitCharts:', splitCharts);
    console.log('chartDataA exists:', !!chartDataA, 'currentExperimentA:', currentExperimentA);
    
    if (!splitCharts) {
        // Overlay mode: rebuild overlay chart
        if (chartDataA) {
            console.log('Rebuilding Chart A with stored data and toggle states (overlay mode)');
            updateChart('A', chartDataA.data, chartDataA.devices, chartDataA.stats, chartDataA.experiment);
        } else if (currentExperimentA) {
            console.log('Rebuilding overlay chart...');
            updateOverlayChart();
        }
    } else {
        // Split mode: rebuild both charts with existing data if available
        console.log('Rebuilding split charts...');
        
        // Always rebuild Chart A if we have stored data
        if (chartDataA) {
            console.log('Rebuilding Chart A with stored data and toggle states');
            updateChart('A', chartDataA.data, chartDataA.devices, chartDataA.stats, chartDataA.experiment);
        } else if (currentExperimentA && currentGroupsA.length > 0) {
            console.log('Loading Chart A from server');
            loadChartData('A');
        }
        
        // Always rebuild Chart B if we have stored data (FIX: This was missing!)
        if (chartDataB) {
            console.log('Rebuilding Chart B with stored data and toggle states');
            updateChart('B', chartDataB.data, chartDataB.devices, chartDataB.stats, chartDataB.experiment);
        } else if (currentExperimentB && currentGroupsB.length > 0) {
            console.log('Loading Chart B from server');
            loadChartData('B');
        }
    }
}

// Toggle overlay/split mode
function toggleOverlay() {
    const chartBContainer = document.getElementById('chartContainerB');
    
    if (!splitCharts) {
        // Overlay mode: Hide chart B container completely
        if (chartBContainer) {
            chartBContainer.style.display = 'none';
        }
        // Show overlay on chart A
        updateOverlayChart();
    } else {
        // Split mode: Show chart B container only if it has data
        if (chartBContainer) {
            if (currentExperimentB && currentGroupsB.length > 0) {
                chartBContainer.style.display = 'block';
                // Load Chart B data if not already loaded
                if (!chartB) {
                    loadChartData('B');
                }
            } else {
                chartBContainer.style.display = 'none';
            }
        }
        // Load separate charts
        if (currentExperimentA && currentGroupsA.length > 0) loadChartData('A');
        if (currentExperimentB && currentGroupsB.length > 0) loadChartData('B');
    }
}

// Update overlay chart (combines A and B)
async function updateOverlayChart() {
    console.log('updateOverlayChart called - showMean:', showMean, 'showMedian:', showMedian, 'showTotal:', showTotal, 'showAverage:', showAverage);
    
    if (!currentExperimentA || !chartA) {
        console.log('updateOverlayChart: Missing currentExperimentA or chartA');
        return;
    }
    
    const experimentA = experiments[currentExperimentA];
    if (!experimentA) {
        console.log('updateOverlayChart: Experiment not found:', currentExperimentA);
        return;
    }
    
    // Use stored data if available (faster, especially for toggles)
    let dataA, dataB;
    if (chartDataA && chartDataA.data) {
        console.log('updateOverlayChart: Using stored chartDataA');
        dataA = {
            data: chartDataA.data,
            devices: chartDataA.devices,
            stats: chartDataA.stats
        };
        dataB = (chartDataB && chartDataB.data) ? {
            data: chartDataB.data,
            devices: chartDataB.devices,
            stats: chartDataB.stats
        } : null;
    } else {
        console.log('updateOverlayChart: Loading data from server');
        // Fallback to loading from server
        dataA = await loadExperimentDataRaw('A', currentExperimentA);
        dataB = currentExperimentB ? await loadExperimentDataRaw('B', currentExperimentB) : null;
    }
    
    if (!dataA || !dataA.data) {
        console.log('updateOverlayChart: No data available');
        return;
    }
    
    console.log('updateOverlayChart: Rebuilding chart with', dataA.data.length, 'data points');
    
    const datasets = [];
    const devicesA = dataA.devices || [];
    const devicesB = dataB ? (dataB.devices || []) : [];
    const curveConfig = getCurveConfig();
    
    // Add device datasets from A (only if showDevices is true)
    if (showDevices) {
        devicesA.forEach((device, index) => {
            const deviceData = dataA.data
                .map(point => ({
                    x: point.timestamp,
                    y: point[device] || null
                }))
                .filter(point => point.y !== null);
            datasets.push({
                label: `A: ${device}`,
                data: deviceData,
                borderColor: deviceColors[index % deviceColors.length],
                borderWidth: 2,
                pointRadius: 0,
                borderDash: [],
                ...curveConfig
            });
        });
        
        // Add device datasets from B
        if (dataB) {
            devicesB.forEach((device, index) => {
                const deviceData = dataB.data
                    .map(point => ({
                        x: point.timestamp,
                        y: point[device] || null
                    }))
                    .filter(point => point.y !== null);
                datasets.push({
                    label: `B: ${device}`,
                    data: deviceData,
                    borderColor: deviceColors[(devicesA.length + index) % deviceColors.length],
                    borderWidth: 2,
                    pointRadius: 0,
                    borderDash: [5, 5],
                    ...curveConfig
                });
            });
        }
    }
    
    // Add statistical overlays with different colors for A vs B
    // Experiment A colors
    const colorA_mean = '#e74c3c';      // Red
    const colorA_median = '#e67e22';    // Orange
    const colorA_total = '#9b59b6';     // Purple
    const colorA_average = '#3498db';   // Blue
    
    // Experiment B colors
    const colorB_mean = '#c0392b';      // Dark Red
    const colorB_median = '#d35400';    // Dark Orange
    const colorB_total = '#8e44ad';     // Dark Purple
    const colorB_average = '#2980b9';   // Dark Blue
    
    if (showMean && dataA.stats) {
        datasets.push({
            label: 'A: Mean',
            data: dataA.data.map(p => ({ x: p.timestamp, y: dataA.stats.mean_watts })),
            borderColor: colorA_mean,
            borderWidth: 3,
            borderDash: [5, 5],
            pointRadius: 0,
            ...curveConfig
        });
        if (dataB && dataB.stats) {
            datasets.push({
                label: 'B: Mean',
                data: dataB.data.map(p => ({ x: p.timestamp, y: dataB.stats.mean_watts })),
                borderColor: colorB_mean,
                borderWidth: 3,
                borderDash: [10, 5],
                pointRadius: 0,
                ...curveConfig
            });
        }
    }
    
    if (showMedian && dataA.stats) {
        datasets.push({
            label: 'A: Median',
            data: dataA.data.map(p => ({ x: p.timestamp, y: dataA.stats.median_watts })),
            borderColor: colorA_median,
            borderWidth: 3,
            borderDash: [5, 5],
            pointRadius: 0,
            ...curveConfig
        });
        if (dataB && dataB.stats) {
            datasets.push({
                label: 'B: Median',
                data: dataB.data.map(p => ({ x: p.timestamp, y: dataB.stats.median_watts })),
                borderColor: colorB_median,
                borderWidth: 3,
                borderDash: [10, 5],
                pointRadius: 0,
                ...curveConfig
            });
        }
    }
    
    if (showTotal && dataA.data.length > 0) {
        // Forward-fill missing values for Experiment A
        const lastKnownValuesA = {};
        devicesA.forEach(dev => { lastKnownValuesA[dev] = null; });
        
        const filledDataA = dataA.data.map(point => {
            const filledPoint = { ...point };
            devicesA.forEach(dev => {
                if (filledPoint[dev] !== null && filledPoint[dev] !== undefined && !isNaN(filledPoint[dev])) {
                    lastKnownValuesA[dev] = filledPoint[dev];
                } else if (lastKnownValuesA[dev] !== null) {
                    filledPoint[dev] = lastKnownValuesA[dev];
                }
            });
            return filledPoint;
        });
        
        const totalDataA = filledDataA
            .map(point => {
                const sum = devicesA.reduce((acc, dev) => {
                    const val = point[dev];
                    return acc + (val !== null && val !== undefined && !isNaN(val) ? val : 0);
                }, 0);
                return { x: point.timestamp, y: sum > 0 ? sum : null };
            })
            .filter(point => point.y !== null);
        datasets.push({
            label: 'A: Total',
            data: totalDataA,
            borderColor: colorA_total,
            borderWidth: 3,
            pointRadius: 0,
            ...curveConfig
        });
        if (dataB && dataB.data.length > 0) {
            // Forward-fill missing values for Experiment B
            const lastKnownValuesB = {};
            devicesB.forEach(dev => { lastKnownValuesB[dev] = null; });
            
            const filledDataB = dataB.data.map(point => {
                const filledPoint = { ...point };
                devicesB.forEach(dev => {
                    if (filledPoint[dev] !== null && filledPoint[dev] !== undefined && !isNaN(filledPoint[dev])) {
                        lastKnownValuesB[dev] = filledPoint[dev];
                    } else if (lastKnownValuesB[dev] !== null) {
                        filledPoint[dev] = lastKnownValuesB[dev];
                    }
                });
                return filledPoint;
            });
            
            const totalDataB = filledDataB
                .map(point => {
                    const sum = devicesB.reduce((acc, dev) => {
                        const val = point[dev];
                        return acc + (val !== null && val !== undefined && !isNaN(val) ? val : 0);
                    }, 0);
                    return { x: point.timestamp, y: sum > 0 ? sum : null };
                })
                .filter(point => point.y !== null);
            datasets.push({
                label: 'B: Total',
                data: totalDataB,
                borderColor: colorB_total,
                borderWidth: 3,
                borderDash: [5, 5],
                pointRadius: 0,
                ...curveConfig
            });
        }
    }
    
    if (showAverage && dataA.data.length > 0) {
        const avgDataA = dataA.data
            .map(point => {
                const values = devicesA.map(dev => point[dev]).filter(v => v !== null && v !== undefined);
                const avg = values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : null;
                return { x: point.timestamp, y: avg };
            })
            .filter(point => point.y !== null);
        datasets.push({
            label: `A: Average (${devicesA.length} devices)`,
            data: avgDataA,
            borderColor: colorA_average,
            borderWidth: 3,
            borderDash: [15, 5],
            pointRadius: 0,
            ...curveConfig
        });
        if (dataB && dataB.data.length > 0) {
            const avgDataB = dataB.data
                .map(point => {
                    const values = devicesB.map(dev => point[dev]).filter(v => v !== null && v !== undefined);
                    const avg = values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : null;
                    return { x: point.timestamp, y: avg };
                })
                .filter(point => point.y !== null);
            datasets.push({
                label: `B: Average (${devicesB.length} devices)`,
                data: avgDataB,
                borderColor: colorB_average,
                borderWidth: 3,
                borderDash: [20, 5],
                pointRadius: 0,
                ...curveConfig
            });
        }
    }
    
    // Clear existing datasets completely before rebuilding
    chartA.data.datasets = [];
    chartA.update('none'); // Clear first
    
    // Set new datasets
    chartA.data.datasets = datasets;
    
    // Add annotation markers for this experiment (as dots below timeline)
    if (dataA && dataA.data) {
        addAnnotationMarkers(chartA, experimentA.name || experimentA.id, dataA.data);
        if (dataB && dataB.data && currentExperimentB) {
            const experimentB = experiments[currentExperimentB];
            if (experimentB) {
                addAnnotationMarkers(chartA, experimentB.name || experimentB.id, dataB.data);
            }
        }
    }
    
    // Force complete chart update
    chartA.update('none'); // Use 'none' mode for faster updates without animation
    
    // Update title
    document.getElementById('chartATitle').textContent = !splitCharts 
        ? `Chart A: ${experimentA.name}${currentExperimentB ? ' (overlaid with ' + experiments[currentExperimentB].name + ')' : ''}`
        : `${experimentA.name} - Power Consumption`;
}

// Load experiment data and return raw result
async function loadExperimentDataRaw(side, experimentId) {
    const experiment = experiments[experimentId];
    if (!experiment || !experiment.devices) return null;
    
    const timeRange = getTimeRange();
    
    try {
        const devicesParam = experiment.devices.join(',');
        const url = `/api/data/power?devices=${encodeURIComponent(devicesParam)}&start=${encodeURIComponent(timeRange.start)}&end=${encodeURIComponent(timeRange.end)}&interval=${currentAggregation}`;
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.success && result.data) {
            return {
                data: result.data,
                devices: result.devices,
                stats: result.stats
            };
        }
        return null;
    } catch (error) {
        console.error(`Error loading experiment ${side}:`, error);
        return null;
    }
}

// Modal functions
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Create experiment
async function createExperiment(event) {
    event.preventDefault();
    
    const name = document.getElementById('experimentName').value;
    const description = document.getElementById('experimentDescription').value;
    const startTime = document.getElementById('experimentStartTime').value;
    const endTime = document.getElementById('experimentEndTime').value;
    const isCurrent = document.getElementById('experimentIsCurrent').checked;
    const checkboxes = document.querySelectorAll('#experimentGroups input[type="checkbox"]:checked');
    const selectedGroups = Array.from(checkboxes).map(cb => cb.value);
    
    if (selectedGroups.length === 0) {
        alert('Please select at least one participant group');
        return;
    }
    
    if (!startTime) {
        alert('Please provide a start time');
        return;
    }
    
    // For current experiments, end_time is optional
    if (!isCurrent && !endTime) {
        alert('Please provide an end time for past experiments');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('name', name);
        formData.append('description', description || '');
        formData.append('start_time', new Date(startTime).toISOString());
        if (endTime) {
            formData.append('end_time', new Date(endTime).toISOString());
        }
        formData.append('is_current', isCurrent ? 'true' : 'false');
        formData.append('linked_groups', selectedGroups.join(','));
        
        const response = await fetch('/api/experiments', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const result = await response.json();
            const experimentId = result.experiment.id;
            experiments[experimentId] = result.experiment;
            populateExperimentSelects();
            populateGroupCheckboxes(); // Refresh in case groups changed
            closeModal('createExperimentModal');
            document.getElementById('createExperimentForm').reset();
            
            // Select the new experiment in Chart A
            document.getElementById('chartAExperiment').value = experimentId;
            currentExperimentA = experimentId;
            populateGroupsForChart('A', experimentId);
            autoSetTimeRangeForExperiment(experimentId);
            // Get selected groups and load chart
            const groupsSelect = document.getElementById('chartAGroups');
            if (groupsSelect) {
                currentGroupsA = Array.from(groupsSelect.selectedOptions).map(opt => opt.value);
                if (currentGroupsA.length > 0) {
                    loadChartData('A');
                }
            }
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to create experiment'}`);
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Add annotation
async function addAnnotation(event) {
    event.preventDefault();
    
    const experimentId = document.getElementById('annotationExperiment').value;
    const label = document.getElementById('annotationLabel').value;
    const description = document.getElementById('annotationDescription').value;
    const color = document.getElementById('annotationColor').value;
    
    // Auto-calculate timestamp from chart's visible time range (center point)
    const timeRange = getTimeRange();
    const startTime = new Date(timeRange.start);
    const endTime = new Date(timeRange.end);
    const centerTime = new Date((startTime.getTime() + endTime.getTime()) / 2);
    
    try {
        const formData = new FormData();
        formData.append('experiment_id', experimentId);
        formData.append('timestamp', centerTime.toISOString());
        formData.append('label', label);
        formData.append('description', description);
        formData.append('color', color);
        
        const response = await fetch('/api/annotations', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            closeModal('addAnnotationModal');
            document.getElementById('addAnnotationForm').reset();
            
            // Reload annotations and refresh charts
            await loadAnnotations();
            if (currentExperimentA && currentGroupsA.length > 0) loadChartData('A');
            if (currentExperimentB && currentGroupsB.length > 0) loadChartData('B');
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to add annotation'}`);
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Save snapshot
async function saveSnapshot(event) {
    event.preventDefault();
    
    const title = document.getElementById('snapshotTitle').value;
    const description = document.getElementById('snapshotDescription').value;
    const experimentId = document.getElementById('snapshotExperiment').value;
    
    if (!currentExperimentA && !currentExperimentB) {
        alert('Please load at least one experiment to save a snapshot');
        return;
    }
    
    const timeRange = getTimeRange();
    
    // Get chart image
    let chartImage = '';
    if (chartA && currentExperimentA) {
        chartImage = chartA.toBase64Image();
    }
    
    // Get experiment
    const experiment = experiments[experimentId];
    if (!experiment) {
        alert('Invalid experiment selected');
        return;
    }
    
    // Get devices from linked groups
    const experimentDevices = [];
    const linkedGroups = experiment.linked_groups || [];
    
    for (const groupName of linkedGroups) {
        const group = groups[groupName];
        if (group && group.devices) {
            experimentDevices.push(...group.devices);
        }
    }
    
    // Remove duplicates
    const uniqueDevices = [...new Set(experimentDevices)];
    
    if (uniqueDevices.length === 0) {
        alert(`Experiment "${experiment.name}" has no devices. Please link groups that contain devices.`);
        return;
    }
    
    try {
        const devicesParam = uniqueDevices.join(',');
        const url = `/api/data/power?devices=${encodeURIComponent(devicesParam)}&start=${encodeURIComponent(timeRange.start)}&end=${encodeURIComponent(timeRange.end)}&interval=${currentAggregation}`;
        
        const response = await fetch(url);
        const result = await response.json();
        
        const formData = new FormData();
        formData.append('title', title);
        formData.append('experiment_id', experimentId);
        formData.append('experiment_name', experiment.name || experimentId);
        formData.append('group_devices', uniqueDevices.join(','));
        formData.append('start_time', timeRange.start);
        formData.append('end_time', timeRange.end);
        formData.append('description', description);
        formData.append('chart_image', chartImage);
        formData.append('energy_stats', JSON.stringify(result.stats || {}));
        formData.append('annotations', JSON.stringify([]));
        
        const saveResponse = await fetch('/api/snapshots', {
            method: 'POST',
            body: formData
        });
        
        if (saveResponse.ok) {
            closeModal('saveSnapshotModal');
            document.getElementById('saveSnapshotForm').reset();
            alert('Snapshot saved successfully!');
        } else {
            const error = await saveResponse.json();
            alert(`Error: ${error.detail || 'Failed to save snapshot'}`);
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Utility functions
function selectAllDevices() {
    document.querySelectorAll('#experimentDevices input[type="checkbox"]').forEach(cb => cb.checked = true);
}

function deselectAllDevices() {
    document.querySelectorAll('#experimentDevices input[type="checkbox"]').forEach(cb => cb.checked = false);
}

// Close modals when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}

// Populate annotation/snapshot experiment selects
function populateExperimentSelectsForModals() {
    const annotationSelect = document.getElementById('annotationExperiment');
    const snapshotSelect = document.getElementById('snapshotExperiment');
    
    [annotationSelect, snapshotSelect].forEach(select => {
        const currentValue = select.value;
        select.innerHTML = '<option value="">-- Select Experiment --</option>';
        
        for (const [name, exp] of Object.entries(experiments)) {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = exp.name || name;
            select.appendChild(option);
        }
        
        if (currentValue) select.value = currentValue;
    });
}

// Update modal selects when experiments change
const originalPopulateExperimentSelects = populateExperimentSelects;
populateExperimentSelects = function() {
    originalPopulateExperimentSelects();
    populateExperimentSelectsForModals();
};

// Reset zoom for a specific chart
function resetZoomForChart(chart) {
    if (!chart) return;
    
    // Use Chart.js zoom plugin resetZoom method if available
    // The zoom plugin adds a resetZoom method to the chart instance
    const zoomPlugin = chart.plugins?.find(p => p.id === 'zoom');
    if (zoomPlugin && chart.resetZoom) {
        try {
            chart.resetZoom();
        } catch (e) {
            console.warn('resetZoom method failed, using fallback:', e);
            resetZoomFallback(chart);
        }
    } else {
        resetZoomFallback(chart);
    }
}

// Fallback zoom reset method
function resetZoomFallback(chart) {
    const xScale = chart.scales?.x;
    if (xScale) {
        // Reset to original min/max (undefined means use data range)
        if (xScale.options) {
            xScale.options.min = undefined;
            xScale.options.max = undefined;
        }
        // Also clear any zoom state
        if (chart.zoomScale) {
            chart.zoomScale = undefined;
        }
        chart.update('none');
    }
}

// Reset zoom for active chart(s)
function resetZoom() {
    if (splitCharts) {
        // Split mode: reset both charts
        if (chartA) resetZoomForChart(chartA);
        if (chartB) resetZoomForChart(chartB);
    } else {
        // Overlay mode: reset Chart A
        if (chartA) resetZoomForChart(chartA);
    }
    
    // Update stats to full range after reset
    if (chartA && chartDataA) {
        updateStatsForVisibleRange(chartA, 'A', chartDataA.data, chartDataA.devices);
    }
    if (chartB && chartDataB) {
        updateStatsForVisibleRange(chartB, 'B', chartDataB.data, chartDataB.devices);
    }
}

// Fullscreen toggle for chart containers
function toggleFullscreen(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    if (!container.classList.contains('fullscreen')) {
        // Enter fullscreen
        container.classList.add('fullscreen');
        
        // Resize charts
        if (containerId === 'chartContainerA' && chartA) {
            setTimeout(() => chartA.resize(), 100);
        } else if (containerId === 'chartContainerB' && chartB) {
            setTimeout(() => chartB.resize(), 100);
        }
    } else {
        // Exit fullscreen
        container.classList.remove('fullscreen');
        
        // Resize charts
        if (containerId === 'chartContainerA' && chartA) {
            setTimeout(() => chartA.resize(), 100);
        } else if (containerId === 'chartContainerB' && chartB) {
            setTimeout(() => chartB.resize(), 100);
        }
    }
}

// Exit fullscreen on Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const fullscreenContainers = document.querySelectorAll('.chart-container.fullscreen');
        fullscreenContainers.forEach(container => {
            container.classList.remove('fullscreen');
            const containerId = container.id;
            if (containerId === 'chartContainerA' && chartA) {
                setTimeout(() => chartA.resize(), 100);
            } else if (containerId === 'chartContainerB' && chartB) {
                setTimeout(() => chartB.resize(), 100);
            }
        });
    }
});

// Collector Control Functions
async function loadCollectorStatus() {
    try {
        const response = await fetch('/api/collector/status');
        if (!response.ok) {
            // Silently fail for collector status - don't spam console
            return;
        }
        const data = await response.json();
        
        // Update UI
        const enabledCheckbox = document.getElementById('collectorEnabled');
        const statusText = document.getElementById('collectorStatusText');
        const runningStatus = document.getElementById('collectorRunningStatus');
        const currentPollInterval = document.getElementById('currentPollInterval');
        const pollIntervalInput = document.getElementById('pollInterval');
        
        if (enabledCheckbox) {
            enabledCheckbox.checked = data.enabled || false;
        }
        
        if (statusText) {
            statusText.textContent = data.running ? 'Running' : 'Stopped';
        }
        
        if (runningStatus) {
            runningStatus.style.color = data.running ? '#27ae60' : '#e74c3c';
            runningStatus.textContent = '●';
        }
        
        if (currentPollInterval) {
            currentPollInterval.textContent = data.poll_interval || 30;
        }
        
        if (pollIntervalInput) {
            pollIntervalInput.value = data.poll_interval || 30;
        }
        
        // Device query delay
        const currentDeviceQueryDelay = document.getElementById('currentDeviceQueryDelay');
        const deviceQueryDelayInput = document.getElementById('deviceQueryDelay');
        
        if (currentDeviceQueryDelay) {
            currentDeviceQueryDelay.textContent = data.device_query_delay ?? 0.5;
        }
        
        if (deviceQueryDelayInput) {
            deviceQueryDelayInput.value = data.device_query_delay ?? 0.5;
        }
    } catch (error) {
        // Silently fail for collector status - don't spam console
        // Only log if it's not a network/timeout error
        if (error.name !== 'TypeError' && !error.message.includes('Failed to fetch')) {
            console.error('Error loading collector status:', error);
        }
    }
}

async function updateCollectorEnabled(enabled) {
    try {
        const formData = new FormData();
        formData.append('enabled', enabled);
        
        const response = await fetch('/api/collector/control', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update status display
            await loadCollectorStatus();
            
            // Show feedback
            const statusText = document.getElementById('collectorStatusText');
            if (statusText) {
                statusText.textContent = enabled ? 'Starting...' : 'Stopping...';
                setTimeout(() => loadCollectorStatus(), 2000);
            }
        } else {
            alert('Failed to update collector status');
        }
    } catch (error) {
        console.error('Error updating collector enabled:', error);
        alert('Error updating collector status: ' + error.message);
    }
}

async function updatePollInterval(interval) {
    try {
        const formData = new FormData();
        formData.append('poll_interval', interval);
        
        const response = await fetch('/api/collector/control', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update status display
            await loadCollectorStatus();
            
            // Show feedback
            const currentPollInterval = document.getElementById('currentPollInterval');
            if (currentPollInterval) {
                currentPollInterval.textContent = interval;
                currentPollInterval.style.color = '#27ae60';
                setTimeout(() => {
                    if (currentPollInterval) {
                        currentPollInterval.style.color = '';
                    }
                }, 2000);
            }
            
            alert(`Polling interval updated to ${interval} seconds. Collector will restart with new settings.`);
        } else {
            alert('Failed to update polling interval');
        }
    } catch (error) {
        console.error('Error updating poll interval:', error);
        alert('Error updating polling interval: ' + error.message);
    }
}

async function updateDeviceQueryDelay(delay) {
    try {
        const formData = new FormData();
        formData.append('device_query_delay', delay);
        
        const response = await fetch('/api/collector/control', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update status display
            await loadCollectorStatus();
            
            // Show feedback
            const currentDeviceQueryDelay = document.getElementById('currentDeviceQueryDelay');
            if (currentDeviceQueryDelay) {
                currentDeviceQueryDelay.textContent = delay;
                currentDeviceQueryDelay.style.color = '#27ae60';
                setTimeout(() => {
                    if (currentDeviceQueryDelay) {
                        currentDeviceQueryDelay.style.color = '';
                    }
                }, 2000);
            }
            
            alert(`Device query delay updated to ${delay} seconds. Collector will restart with new settings.`);
        } else {
            alert('Failed to update device query delay');
        }
    } catch (error) {
        console.error('Error updating device query delay:', error);
        alert('Error updating device query delay: ' + error.message);
    }
}


// ============================================================================
// Auto-Update Functions
// ============================================================================

// Start auto-update interval (refreshes chart data every 30 seconds)
function startAutoUpdate() {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
    
    // Update every 30 seconds (adjust as needed)
    updateInterval = setInterval(() => {
        if (autoUpdate) {
            refreshCurrentCharts();
        }
    }, 30000); // 30 seconds
    
    console.log('Auto-update started (refreshes every 30 seconds)');
}

// Stop auto-update interval
function stopAutoUpdate() {
    if (updateInterval) {
        clearInterval(updateInterval);
        updateInterval = null;
        console.log('Auto-update stopped');
    }
}

// Toggle auto-update on/off
function toggleAutoUpdate() {
    autoUpdate = !autoUpdate;
    const btn = document.getElementById('autoUpdateBtn');
    
    if (autoUpdate) {
        btn.textContent = '⏸️ Pause Updates';
        btn.title = 'Pause auto-updates to study current view';
        startAutoUpdate();
    } else {
        btn.textContent = '▶️ Resume Updates';
        btn.title = 'Resume auto-updates to see latest data';
        stopAutoUpdate();
    }
}

// Track last successful refresh to avoid spam on failures
let lastRefreshSuccess = true;
let consecutiveFailures = 0;

// Refresh current charts with latest data (only if auto-update is enabled)
async function refreshCurrentCharts() {
    if (!autoUpdate) return;
    
    // If we've had too many consecutive failures, skip this refresh to avoid spam
    if (!lastRefreshSuccess && consecutiveFailures > 2) {
        console.log('Skipping auto-refresh - too many consecutive failures');
        return;
    }
    
    // Only refresh if we have active charts
    try {
        if (currentExperimentA && currentGroupsA.length > 0) {
            console.log('Auto-refreshing Chart A...');
            await loadChartData('A');
            
            // Auto-scroll to latest time
            if (chartA && chartA.data.datasets.length > 0) {
                autoScrollToLatest(chartA);
            }
            lastRefreshSuccess = true;
            consecutiveFailures = 0;
        } else if (chartDataA && chartDataA.experiment && chartDataA.experiment.id === 'all-devices') {
            // Default chart case - reload with current time range
            console.log('Auto-refreshing default chart...');
            await reloadDefaultChartWithCurrentTimeRange();
            
            // Auto-scroll to latest time
            if (chartA && chartA.data.datasets.length > 0) {
                autoScrollToLatest(chartA);
            }
            lastRefreshSuccess = true;
            consecutiveFailures = 0;
        }
        
        if (splitCharts && currentExperimentB && currentGroupsB.length > 0) {
            console.log('Auto-refreshing Chart B...');
            await loadChartData('B');
            
            // Auto-scroll to latest time
            if (chartB && chartB.data.datasets.length > 0) {
                autoScrollToLatest(chartB);
            }
        }
    } catch (error) {
        lastRefreshSuccess = false;
        consecutiveFailures++;
        console.warn(`Auto-refresh failed (${consecutiveFailures} consecutive):`, error);
        // Don't show alert for auto-refresh failures to avoid spam
    }
}

// Auto-scroll chart to show the latest data point
function autoScrollToLatest(chart) {
    if (!chart || !chart.data.datasets || chart.data.datasets.length === 0) return;
    
    // Find the latest timestamp across all datasets
    let latestTime = null;
    chart.data.datasets.forEach(dataset => {
        if (dataset.data && dataset.data.length > 0) {
            dataset.data.forEach(point => {
                if (point && point.x) {
                    const time = new Date(point.x).getTime();
                    if (!latestTime || time > latestTime) {
                        latestTime = time;
                    }
                }
            });
        }
    });
    
    if (!latestTime) return;
    
    // Get current scale limits
    const xScale = chart.scales.x;
    if (!xScale) return;
    
    // Calculate time range based on current view width
    const currentMin = xScale.min;
    const currentMax = xScale.max;
    const viewWidth = currentMax - currentMin;
    
    // Set new limits to show latest data at the right edge
    const newMax = latestTime;
    const newMin = newMax - viewWidth;
    
    // Update chart scale limits
    chart.options.scales.x.min = newMin;
    chart.options.scales.x.max = newMax;
    chart.update('none');
}

// Helper function to update experiment start time in backend
async function updateExperimentStartTime(experimentId, startTime) {
    try {
        const formData = new FormData();
        formData.append('start_time', startTime);
        
        const response = await fetch(`/api/experiments/${experimentId}`, {
            method: 'PUT',
            body: formData
        });
        
        if (response.ok) {
            console.log(`Auto-set start time for experiment ${experimentId} to ${startTime}`);
        } else {
            console.warn(`Failed to auto-set start time for experiment ${experimentId}`);
        }
    } catch (error) {
        console.error('Error updating experiment start time:', error);
    }
}
