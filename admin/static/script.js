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

// Set up event listeners for edit/delete buttons using data attributes
document.addEventListener('DOMContentLoaded', () => {
    // Handle click events on buttons with data-action attribute using event delegation
    document.addEventListener('click', (event) => {
        const btn = event.target.closest('[data-action]');
        if (!btn) return;
        
        const action = btn.getAttribute('data-action');
        const groupName = btn.getAttribute('data-group');
        
        if (action === 'edit' && groupName) {
            event.preventDefault();
            event.stopPropagation();
            editGroup(groupName);
        } else if (action === 'delete' && groupName) {
            event.preventDefault();
            event.stopPropagation();
            deleteGroup(groupName);
        }
    });
});

