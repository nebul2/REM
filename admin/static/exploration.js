// GOS REM Data Exploration - Complete JavaScript

// Global state
let chartA = null;
let chartB = null;
let currentExperimentA = null;
let currentExperimentB = null;
let currentTimeRange = '1h';
let currentAggregation = '1m';
let allDevices = [];
let experiments = {};
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

// Colors for device lines
const deviceColors = [
    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
    '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384'
];

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
        
        // Load experiments (groups)
        console.log('Loading groups/experiments...');
        const groupsRes = await fetch('/api/groups');
        if (!groupsRes.ok) {
            throw new Error(`Failed to load groups: ${groupsRes.status}`);
        }
        const groupsData = await groupsRes.json();
        experiments = groupsData.groups || {};
        console.log(`Loaded ${Object.keys(experiments).length} experiments/groups:`, Object.keys(experiments));
        
        populateExperimentSelects();
        populateDeviceCheckboxes();
        
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
    document.getElementById('experimentA').addEventListener('change', (e) => {
        currentExperimentA = e.target.value;
        if (currentExperimentA) loadExperimentData('A', currentExperimentA);
    });
    
    document.getElementById('experimentB').addEventListener('change', (e) => {
        currentExperimentB = e.target.value;
        if (currentExperimentB) loadExperimentData('B', currentExperimentB);
    });
    
    document.getElementById('timeRange').addEventListener('change', (e) => {
        currentTimeRange = e.target.value;
        if (currentTimeRange === 'custom') {
            document.getElementById('customRange').style.display = 'flex';
        } else {
            document.getElementById('customRange').style.display = 'none';
            if (currentExperimentA) loadExperimentData('A', currentExperimentA);
            if (currentExperimentB) loadExperimentData('B', currentExperimentB);
        }
    });
    
    document.getElementById('applyCustomRange').addEventListener('click', () => {
        if (currentExperimentA) loadExperimentData('A', currentExperimentA);
        if (currentExperimentB) loadExperimentData('B', currentExperimentB);
    });
    
    document.getElementById('aggregation').addEventListener('change', (e) => {
        currentAggregation = e.target.value;
        if (currentExperimentA) loadExperimentData('A', currentExperimentA);
        if (currentExperimentB) loadExperimentData('B', currentExperimentB);
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
        updateCharts();
    });
    
    document.getElementById('showMedian').addEventListener('change', (e) => {
        showMedian = e.target.checked;
        updateCharts();
    });
    
    document.getElementById('showTotal').addEventListener('change', (e) => {
        showTotal = e.target.checked;
        updateCharts();
    });
    
    document.getElementById('showAverage').addEventListener('change', (e) => {
        showAverage = e.target.checked;
        updateCharts();
    });
    
    document.getElementById('splitCharts').addEventListener('change', (e) => {
        splitCharts = e.target.checked;
        toggleOverlay();
    });
    
    // Buttons
    document.getElementById('createExperimentBtn').addEventListener('click', () => {
        openModal('createExperimentModal');
    });
    
    document.getElementById('addAnnotationBtn').addEventListener('click', () => {
        openModal('addAnnotationModal');
    });
    
    document.getElementById('saveSnapshotBtn').addEventListener('click', () => {
        openModal('saveSnapshotModal');
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
    
    // Load collector status on page load
    loadCollectorStatus();
    
    // Refresh collector status every 10 seconds
    setInterval(loadCollectorStatus, 10000);
    
    document.getElementById('refreshBtn').addEventListener('click', () => {
        if (currentExperimentA) loadExperimentData('A', currentExperimentA);
        if (currentExperimentB) loadExperimentData('B', currentExperimentB);
    });
}

// Populate experiment selects
function populateExperimentSelects() {
    const selectA = document.getElementById('experimentA');
    const selectB = document.getElementById('experimentB');
    
    // Clear options except first
    selectA.innerHTML = '<option value="">-- Select Experiment --</option>';
    selectB.innerHTML = '<option value="">-- Select Experiment --</option>';
    
    for (const [name, exp] of Object.entries(experiments)) {
        const optionA = document.createElement('option');
        optionA.value = name;
        optionA.textContent = exp.name || name;
        selectA.appendChild(optionA);
        
        const optionB = document.createElement('option');
        optionB.value = name;
        optionB.textContent = exp.name || name;
        selectB.appendChild(optionB);
    }
}

// Populate device checkboxes
function populateDeviceCheckboxes() {
    const container = document.getElementById('experimentDevices');
    container.innerHTML = '';
    
    allDevices.forEach(device => {
        const label = document.createElement('label');
        label.className = 'checkbox-label';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.name = 'devices';
        checkbox.value = device;
        
        const span = document.createElement('span');
        span.textContent = device;
        
        label.appendChild(checkbox);
        label.appendChild(span);
        container.appendChild(label);
    });
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
        default:
            start = new Date(now - 60 * 60 * 1000);
    }
    
    return {
        start: start.toISOString(),
        end: now.toISOString()
    };
}

// Load experiment data
async function loadExperimentData(side, experimentName) {
    const experiment = experiments[experimentName];
    if (!experiment || !experiment.devices || experiment.devices.length === 0) {
        console.error('Invalid experiment:', experimentName);
        return;
    }
    
    const timeRange = getTimeRange();
    
    try {
        const devicesParam = experiment.devices.join(',');
        const url = `/api/data/power?devices=${encodeURIComponent(devicesParam)}&start=${encodeURIComponent(timeRange.start)}&end=${encodeURIComponent(timeRange.end)}&interval=${currentAggregation}`;
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.success && result.data) {
            updateChart(side, result.data, result.devices, result.stats, experiment);
        }
    } catch (error) {
        console.error(`Error loading experiment ${side}:`, error);
    }
}

// Initialize charts
function initializeCharts() {
    const ctxA = document.getElementById('chartA').getContext('2d');
    const ctxB = document.getElementById('chartB').getContext('2d');
    
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
                        
                        // Let Chart.js handle the default toggle behavior for device datasets
                        const meta = chart.getDatasetMeta(index);
                        meta.hidden = meta.hidden === null ? !dataset.hidden : null;
                        
                        // Recalculate statistics based on visible devices after toggle
                        setTimeout(() => recalculateStatisticsForChart(chart), 100);
                    }
                },
                tooltip: {
                    mode: 'nearest',
                    intersect: true,
                    callbacks: {
                        title: function(context) {
                            // Show timestamp
                            return context[0].label;
                        },
                        label: function(context) {
                            // Show only the hovered line's label and value
                            const label = context.dataset.label || '';
                            const value = context.parsed.y !== null ? context.parsed.y.toFixed(1) + ' W' : 'N/A';
                            return `${label}: ${value}`;
                        },
                        filter: function(tooltipItem) {
                            // Only show the first item (the one being hovered)
                            return tooltipItem.datasetIndex === tooltipItem.dataIndex || tooltipItem.elementIndex === 0;
                        }
                    }
                },
                annotation: {
                    annotations: {}
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
    
    // Add click handlers for annotation markers
    setupAnnotationClickHandlers(chartA);
    setupAnnotationClickHandlers(chartB);
    
    // Note: Zoom/pan stats updates are handled by the zoom plugin callbacks
    // which are configured in the chart options if needed
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
    
    if (!chart) return;
    
    // Store chart data for recalculation
    if (side === 'A') {
        chartDataA = { data, devices, stats, experiment };
    } else {
        chartDataB = { data, devices, stats, experiment };
    }
    
    titleEl.textContent = `${experiment.name || experiment} - Power Consumption`;
    
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
            // Filter out null values for smoother lines
            const deviceData = data
                .map(point => ({
                    x: point.timestamp,
                    y: point[device] || null
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
        const totalData = data
            .map(point => {
                const sum = devices.reduce((acc, dev) => acc + (point[dev] || 0), 0);
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
    
    chart.data.datasets = datasets;
    
    // Add annotation markers for this experiment (as dots below timeline)
    addAnnotationMarkers(chart, experiment.name || experiment, data);
    
    chart.update();
    
    // Store chart data for legend-based recalculation
    if (side === 'A') {
        chartDataA = { data, devices, stats, experiment };
    } else {
        chartDataB = { data, devices, stats, experiment };
    }
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
        
        // Total (Sum)
        if (showTotal) {
            const totalData = allValues.map(item => {
                if (item.values.length === 0) return null;
                const sum = item.values.reduce((a, b) => a + b, 0);
                return { x: item.timestamp, y: sum > 0 ? sum : null };
            }).filter(p => p !== null && p.y !== null);
            
            newStatDatasets.push({
                label: side ? `${side}: Total` : 'Total (Sum)',
                data: totalData,
                borderColor: side === 'A' ? '#9b59b6' : (side === 'B' ? '#8e44ad' : 'purple'),
                borderWidth: 3,
                pointRadius: 0,
                fill: false,
                ...curveConfig
            });
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
    if (!splitCharts) {
        updateOverlayChart();
    } else {
        if (currentExperimentA) loadExperimentData('A', currentExperimentA);
        if (currentExperimentB) loadExperimentData('B', currentExperimentB);
    }
}

// Toggle overlay/split mode
function toggleOverlay() {
    const chartBContainer = document.querySelector('.charts-section > .chart-container:last-child');
    if (!splitCharts) {
        // Overlay mode: Hide chart B container
        if (chartBContainer) chartBContainer.style.display = 'none';
        // Show overlay on chart A
        updateOverlayChart();
    } else {
        // Split mode: Show chart B container
        if (chartBContainer) chartBContainer.style.display = 'block';
        // Load separate charts
        if (currentExperimentA) loadExperimentData('A', currentExperimentA);
        if (currentExperimentB) loadExperimentData('B', currentExperimentB);
    }
}

// Update overlay chart (combines A and B)
async function updateOverlayChart() {
    if (!currentExperimentA || !chartA) return;
    
    const experimentA = experiments[currentExperimentA];
    if (!experimentA) return;
    
    const dataA = await loadExperimentDataRaw('A', currentExperimentA);
    const dataB = currentExperimentB ? await loadExperimentDataRaw('B', currentExperimentB) : null;
    
    if (!dataA || !dataA.data) return;
    
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
        const totalDataA = dataA.data
            .map(point => {
                const sum = devicesA.reduce((acc, dev) => acc + (point[dev] || 0), 0);
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
            const totalDataB = dataB.data
                .map(point => {
                    const sum = devicesB.reduce((acc, dev) => acc + (point[dev] || 0), 0);
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
    
    chartA.data.datasets = datasets;
    chartA.update();
    
    // Update title
    document.getElementById('chartATitle').textContent = !splitCharts 
        ? `Overlay: ${experimentA.name}${currentExperimentB ? ' vs ' + experiments[currentExperimentB].name : ''}`
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
    const checkboxes = document.querySelectorAll('#experimentDevices input[type="checkbox"]:checked');
    const devices = Array.from(checkboxes).map(cb => cb.value);
    
    if (devices.length === 0) {
        alert('Please select at least one device');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('name', name);
        formData.append('devices', devices.join(','));
        formData.append('description', description);
        
        const response = await fetch('/api/experiments', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const result = await response.json();
            experiments[name] = result.experiment;
            populateExperimentSelects();
            closeModal('createExperimentModal');
            document.getElementById('createExperimentForm').reset();
            
            // Select the new experiment
            document.getElementById('experimentA').value = name;
            currentExperimentA = name;
            loadExperimentData('A', name);
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
            if (currentExperimentA) loadExperimentData('A', currentExperimentA);
            if (currentExperimentB) loadExperimentData('B', currentExperimentB);
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
    
    // Get energy stats
    const experiment = experiments[experimentId];
    if (!experiment) {
        alert('Invalid experiment selected');
        return;
    }
    
    try {
        const devicesParam = experiment.devices.join(',');
        const url = `/api/data/power?devices=${encodeURIComponent(devicesParam)}&start=${encodeURIComponent(timeRange.start)}&end=${encodeURIComponent(timeRange.end)}&interval=${currentAggregation}`;
        
        const response = await fetch(url);
        const result = await response.json();
        
        const formData = new FormData();
        formData.append('title', title);
        formData.append('experiment_id', experimentId);
        formData.append('experiment_name', experiment.name || experimentId);
        formData.append('group_devices', experiment.devices.join(','));
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
    } catch (error) {
        console.error('Error loading collector status:', error);
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

