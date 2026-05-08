// Device management functions
function selectAll() {
    const checkboxes = document.querySelectorAll('#deviceCheckboxes input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = true);
}

function selectNone() {
    const checkboxes = document.querySelectorAll('#deviceCheckboxes input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = false);
}

function selectAllEdit() {
    const checkboxes = document.querySelectorAll('#editDeviceCheckboxes input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = true);
}

function selectNoneEdit() {
    const checkboxes = document.querySelectorAll('#editDeviceCheckboxes input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = false);
}

// Create group
async function createGroup(event) {
    event.preventDefault();
    
    const groupName = document.getElementById('groupName').value.trim();
    const checkboxes = document.querySelectorAll('#deviceCheckboxes input[type="checkbox"]:checked');
    const devices = Array.from(checkboxes).map(cb => cb.value);
    
    if (!groupName) {
        alert('Please enter a group name');
        return;
    }
    
    if (devices.length === 0) {
        alert('Please select at least one device');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('name', groupName);
        formData.append('devices', devices.join(','));
        
        const response = await fetch('/api/groups', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            window.location.reload();
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to create group'}`);
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Delete group - make it globally accessible
window.deleteGroup = async function(groupName) {
    if (!confirm(`Are you sure you want to delete group "${groupName}"?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/groups/${encodeURIComponent(groupName)}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            window.location.reload();
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to delete group'}`);
        }
    } catch (error) {
        console.error('Delete group error:', error);
        alert(`Error: ${error.message}`);
    }
}

// Edit group - make it globally accessible
window.editGroup = async function(groupName) {
    try {
        const response = await fetch('/api/groups');
        const data = await response.json();
        const group = data.groups[groupName];
        
        if (!group) {
            alert('Group not found');
            return;
        }
        
        document.getElementById('editGroupName').textContent = groupName;
        
        // Get all available devices
        const devicesResponse = await fetch('/api/devices');
        const devicesData = await devicesResponse.json();
        const allDevices = devicesData.devices;
        
        // Populate checkboxes
        const container = document.getElementById('editDeviceCheckboxes');
        container.innerHTML = '';
        
        allDevices.forEach(device => {
            const label = document.createElement('label');
            label.className = 'checkbox-label';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.name = 'devices';
            checkbox.value = device;
            checkbox.checked = group.devices.includes(device);
            
            const span = document.createElement('span');
            span.textContent = device;
            
            label.appendChild(checkbox);
            label.appendChild(span);
            container.appendChild(label);
        });
        
        // Store current group name for update
        document.getElementById('editGroupForm').dataset.groupName = groupName;
        
        // Show modal
        document.getElementById('editModal').style.display = 'block';
    } catch (error) {
        console.error('Edit group error:', error);
        alert(`Error: ${error.message}`);
    }
}

// Update group
async function updateGroup(event) {
    event.preventDefault();
    
    const groupName = document.getElementById('editGroupForm').dataset.groupName;
    const checkboxes = document.querySelectorAll('#editDeviceCheckboxes input[type="checkbox"]:checked');
    const devices = Array.from(checkboxes).map(cb => cb.value);
    
    if (devices.length === 0) {
        alert('Please select at least one device');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('devices', devices.join(','));
        
        const response = await fetch(`/api/groups/${encodeURIComponent(groupName)}`, {
            method: 'PUT',
            body: formData
        });
        
        if (response.ok) {
            window.location.reload();
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to update group'}`);
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Close edit modal
function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('editModal');
    if (event.target === modal) {
        closeEditModal();
    }
}

// ----------------------------------------------------------------------------
// Fleet (device registry) handlers
// ----------------------------------------------------------------------------

window.refreshFleet = async function () {
    const btn = document.getElementById('refreshFleetBtn');
    const summary = document.getElementById('fleetSummary');
    if (!btn) return;
    const originalLabel = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Refreshing…';
    if (summary) summary.classList.add('refreshing');

    try {
        const response = await fetch('/api/devices/refresh-fleet', { method: 'POST' });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            alert(`Refresh failed: ${err.detail || response.statusText}`);
            return;
        }
        // Reload — server-rendered registry is the source of truth for the page
        window.location.reload();
    } catch (e) {
        alert(`Refresh error: ${e.message}`);
    } finally {
        btn.disabled = false;
        btn.textContent = originalLabel;
        if (summary) summary.classList.remove('refreshing');
    }
};

async function setLifecycle(alias, action) {
    const url = `/api/devices/${encodeURIComponent(alias)}/${action}`;
    try {
        const response = await fetch(url, { method: 'POST' });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            alert(`Failed to ${action} ${alias}: ${err.detail || response.statusText}`);
            return;
        }
        window.location.reload();
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

// ----------------------------------------------------------------------------
// Relative time rendering — turn ISO8601 timestamps into "3 min ago"
// ----------------------------------------------------------------------------

function relativeTime(iso) {
    if (!iso) return '';
    const then = new Date(iso);
    if (isNaN(then.getTime())) return iso;
    const diffSec = Math.floor((Date.now() - then.getTime()) / 1000);
    if (diffSec < 5) return 'just now';
    if (diffSec < 60) return `${diffSec}s ago`;
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)} min ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} h ago`;
    return `${Math.floor(diffSec / 86400)} d ago`;
}

function renderRelativeTimes() {
    document.querySelectorAll('[data-rel-time]').forEach(el => {
        const iso = el.getAttribute('data-rel-time');
        el.textContent = relativeTime(iso);
        el.title = iso;
    });
}

// ----------------------------------------------------------------------------
// Set up event listeners for edit/delete + lifecycle buttons
// ----------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    renderRelativeTimes();

    // Handle click events on buttons with data-action attribute using event delegation
    document.addEventListener('click', (event) => {
        const btn = event.target.closest('[data-action]');
        if (!btn) return;

        const action = btn.getAttribute('data-action');
        const groupName = btn.getAttribute('data-group');
        const alias = btn.getAttribute('data-alias');

        if (action === 'edit' && groupName) {
            event.preventDefault();
            event.stopPropagation();
            editGroup(groupName);
        } else if (action === 'delete' && groupName) {
            event.preventDefault();
            event.stopPropagation();
            deleteGroup(groupName);
        } else if (action === 'exclude' && alias) {
            event.preventDefault();
            event.stopPropagation();
            if (confirm(`Exclude ${alias}? Collector will stop polling it. You can reactivate later.`)) {
                setLifecycle(alias, 'exclude');
            }
        } else if (action === 'archive' && alias) {
            event.preventDefault();
            event.stopPropagation();
            if (confirm(`Archive ${alias}? Marks it retired; historical data is preserved.`)) {
                setLifecycle(alias, 'archive');
            }
        } else if (action === 'reactivate' && alias) {
            event.preventDefault();
            event.stopPropagation();
            setLifecycle(alias, 'reactivate');
        }
    });
});

