// Gallery JavaScript

let allSnapshots = {};

document.addEventListener('DOMContentLoaded', async () => {
    await loadSnapshots();
    setupEventListeners();
});

async function loadSnapshots() {
    try {
        const response = await fetch('/api/snapshots');
        const result = await response.json();
        allSnapshots = result.snapshots || {};
        displaySnapshots(allSnapshots);
        populateExperimentFilter();
    } catch (error) {
        console.error('Error loading snapshots:', error);
    }
}

function setupEventListeners() {
    document.getElementById('applyFilters').addEventListener('click', applyFilters);
    document.getElementById('clearFilters').addEventListener('click', clearFilters);
    document.getElementById('searchInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') applyFilters();
    });
}

function populateExperimentFilter() {
    const select = document.getElementById('filterExperiment');
    
    fetch('/api/experiments')
        .then(res => res.json())
        .then(data => {
            const experiments = data.experiments || {};
            select.innerHTML = '<option value="">All Experiments</option>';
            
            for (const [name, exp] of Object.entries(experiments)) {
                const option = document.createElement('option');
                option.value = name;
                option.textContent = exp.name || name;
                select.appendChild(option);
            }
        });
}

function applyFilters() {
    const experiment = document.getElementById('filterExperiment').value;
    const search = document.getElementById('searchInput').value.toLowerCase();
    
    let filtered = { ...allSnapshots };
    
    if (experiment) {
        filtered = Object.fromEntries(
            Object.entries(filtered).filter(([id, snap]) => 
                snap.experiment_id === experiment
            )
        );
    }
    
    if (search) {
        filtered = Object.fromEntries(
            Object.entries(filtered).filter(([id, snap]) => 
                (snap.title || '').toLowerCase().includes(search) ||
                (snap.description || '').toLowerCase().includes(search)
            )
        );
    }
    
    displaySnapshots(filtered);
}

function clearFilters() {
    document.getElementById('filterExperiment').value = '';
    document.getElementById('searchInput').value = '';
    displaySnapshots(allSnapshots);
}

function displaySnapshots(snapshots) {
    const grid = document.getElementById('galleryGrid');
    
    if (Object.keys(snapshots).length === 0) {
        grid.innerHTML = '<div class="empty-state"><p>No snapshots found. Create your first snapshot from the Exploration page!</p></div>';
        return;
    }
    
    grid.innerHTML = '';
    
    // Sort by created_at (newest first)
    const sorted = Object.entries(snapshots).sort((a, b) => {
        const dateA = new Date(a[1].created_at || 0);
        const dateB = new Date(b[1].created_at || 0);
        return dateB - dateA;
    });
    
    sorted.forEach(([id, snapshot]) => {
        const card = createSnapshotCard(id, snapshot);
        grid.appendChild(card);
    });
}

function createSnapshotCard(id, snapshot) {
    const card = document.createElement('div');
    card.className = 'snapshot-card';
    
    const createdDate = new Date(snapshot.created_at);
    const timeRange = snapshot.time_range || {};
    const stats = snapshot.energy_stats || {};
    
    card.innerHTML = `
        <div class="snapshot-image">
            ${snapshot.image_path ? 
                `<img src="/api/snapshots/${snapshot.id}/image" alt="${snapshot.title}" onerror="this.style.display='none'">` :
                '<div class="no-image">No Image</div>'
            }
        </div>
        <div class="snapshot-info">
            <h3>${snapshot.title || 'Untitled'}</h3>
            <p class="snapshot-meta">
                <strong>Experiment:</strong> ${snapshot.experiment_name || snapshot.experiment_id || 'Unknown'}<br>
                ${snapshot.group_members && snapshot.group_members.length > 0 ? `<strong>Group Members:</strong> ${snapshot.group_members.length} device(s)<br>` : ''}
                <strong>Created:</strong> ${createdDate.toLocaleString()}<br>
                ${timeRange.start ? `<strong>Time Range:</strong> ${new Date(timeRange.start).toLocaleString()} - ${new Date(timeRange.end).toLocaleString()}<br>` : ''}
            </p>
            ${stats.total_kwh ? `
                <div class="snapshot-stats">
                    <span>Total: ${stats.total_kwh.toFixed(2)} kWh</span>
                    <span>Avg: ${stats.average_watts ? stats.average_watts.toFixed(1) : 0} W</span>
                </div>
            ` : ''}
            ${snapshot.description ? `<p class="snapshot-description">${snapshot.description}</p>` : ''}
            <div class="snapshot-actions">
                <button onclick="viewSnapshot('${id}')" class="btn btn-primary">View</button>
                <button onclick="deleteSnapshot('${id}')" class="btn btn-secondary">Delete</button>
            </div>
        </div>
    `;
    
    return card;
}

function viewSnapshot(id) {
    const snapshot = allSnapshots[id];
    if (!snapshot) return;
    
    const modal = document.getElementById('snapshotDetailModal');
    const content = document.getElementById('snapshotDetailContent');
    
    const createdDate = new Date(snapshot.created_at);
    const timeRange = snapshot.time_range || {};
    const stats = snapshot.energy_stats || {};
    
    content.innerHTML = `
        <div class="snapshot-header-actions">
            <h2>${snapshot.title || 'Untitled'}</h2>
            <div class="snapshot-action-buttons">
                <button onclick="toggleGalleryFullscreen()" class="btn btn-secondary" title="Fullscreen">
                    ⛶ Fullscreen
                </button>
                <button onclick="downloadSnapshot('${snapshot.id}', '${snapshot.title || 'snapshot'}')" class="btn btn-primary" title="Download">
                    ⬇ Download
                </button>
            </div>
        </div>
        <div class="snapshot-detail">
            ${snapshot.image_path ? 
                `<div class="snapshot-detail-image">
                    <img id="snapshot-image-${snapshot.id}" src="/api/snapshots/${snapshot.id}/image" alt="${snapshot.title}" style="max-width: 100%; height: auto;">
                </div>` :
                '<p>No image available</p>'
            }
            <div class="snapshot-detail-info">
                <h3>Experiment Details</h3>
                <p><strong>Experiment:</strong> ${snapshot.experiment_name || snapshot.experiment_id || 'Unknown'}</p>
                ${snapshot.group_members && snapshot.group_members.length > 0 ? `
                    <p><strong>Group Members (${snapshot.group_members.length} devices):</strong></p>
                    <ul style="margin-left: 20px; margin-top: 5px;">
                        ${snapshot.group_members.map(device => `<li>${device}</li>`).join('')}
                    </ul>
                ` : ''}
                <p><strong>Snapshot Created:</strong> ${createdDate.toLocaleString()}</p>
                ${timeRange.start ? `
                    <h3>Time Range</h3>
                    <p><strong>Start Time:</strong> ${new Date(timeRange.start).toLocaleString()}</p>
                    <p><strong>End Time:</strong> ${new Date(timeRange.end).toLocaleString()}</p>
                ` : ''}
                ${snapshot.description ? `<p><strong>Notes:</strong> ${snapshot.description}</p>` : ''}
                
                ${snapshot.annotations && snapshot.annotations.length > 0 ? `
                    <h3>Annotations</h3>
                    <div class="snapshot-annotations">
                        ${snapshot.annotations.map(ann => {
                            const annTime = new Date(ann.timestamp);
                            return `
                                <div class="annotation-item" style="border-left: 3px solid ${ann.color || '#007bff'}; padding-left: 10px; margin-bottom: 10px;">
                                    <p><strong>${ann.label || 'Untitled'}</strong> <span style="color: #666; font-size: 0.9em;">(${annTime.toLocaleString()})</span></p>
                                    ${ann.description ? `<p style="margin-top: 5px; color: #666;">${ann.description}</p>` : ''}
                                </div>
                            `;
                        }).join('')}
                    </div>
                ` : ''}
                
                ${stats.total_kwh ? `
                    <h3>Energy Statistics</h3>
                    <div class="snapshot-detail-stats">
                        <p>Total Energy: <strong>${stats.total_kwh.toFixed(2)} kWh</strong></p>
                        <p>Average Power: <strong>${stats.average_watts ? stats.average_watts.toFixed(1) : 0} W</strong></p>
                        <p>Mean: <strong>${stats.mean_watts ? stats.mean_watts.toFixed(1) : 0} W</strong></p>
                        <p>Median: <strong>${stats.median_watts ? stats.median_watts.toFixed(1) : 0} W</strong></p>
                        <p>Min: <strong>${stats.min_watts ? stats.min_watts.toFixed(1) : 0} W</strong></p>
                        <p>Max: <strong>${stats.max_watts ? stats.max_watts.toFixed(1) : 0} W</strong></p>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
    
    modal.style.display = 'block';
}

async function deleteSnapshot(id) {
    if (!confirm('Are you sure you want to delete this snapshot?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/snapshots/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            delete allSnapshots[id];
            displaySnapshots(allSnapshots);
            alert('Snapshot deleted successfully!');
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to delete snapshot'}`);
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('fullscreen');
    }
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
        event.target.classList.remove('fullscreen');
    }
}

// Fullscreen toggle for gallery modal
function toggleGalleryFullscreen() {
    const modal = document.getElementById('snapshotDetailModal');
    if (!modal) return;
    
    if (!modal.classList.contains('fullscreen')) {
        // Enter fullscreen
        modal.classList.add('fullscreen');
    } else {
        // Exit fullscreen
        modal.classList.remove('fullscreen');
    }
}

// Download snapshot as ZIP (image + CSV)
async function downloadSnapshot(snapshotId, title) {
    try {
        const zipUrl = `/api/snapshots/${snapshotId}/download`;
        const response = await fetch(zipUrl);
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to download ZIP: ${response.status} ${errorText}`);
        }
        
        const blob = await response.blob();
        if (!blob || blob.size === 0) {
            throw new Error('Received empty ZIP file');
        }
        
        // Get filename from Content-Disposition header or generate one
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `${(title || 'snapshot').replace(/[^a-z0-9]/gi, '_')}-${snapshotId.substring(0, 8)}.zip`;
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/i);
            if (filenameMatch) {
                filename = filenameMatch[1];
            }
        }
        
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        
        // Clean up after a short delay
        setTimeout(() => {
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        }, 100);
    } catch (error) {
        console.error('Download error:', error);
        alert(`Error downloading snapshot: ${error.message}\n\nPlease check the browser console for details.`);
    }
}

// Exit fullscreen on Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const fullscreenModal = document.querySelector('#snapshotDetailModal.fullscreen');
        if (fullscreenModal) {
            fullscreenModal.classList.remove('fullscreen');
        }
    }
});

