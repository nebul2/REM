// Experiments management functions

// Load and display experiments
async function loadExperiments() {
    try {
        const response = await fetch('/api/experiments');
        const data = await response.json();
        const experiments = data.experiments || {};
        
        const container = document.getElementById('experimentsList');
        
        if (Object.keys(experiments).length === 0) {
            container.innerHTML = '<p class="empty-state">No experiments created yet. Click "Create Experiment" above to get started!</p>';
            return;
        }
        
        container.innerHTML = '';
        
        // Sort experiments by creation date (newest first)
        const sortedExperiments = Object.entries(experiments).sort((a, b) => {
            const dateA = new Date(a[1].created_at || 0);
            const dateB = new Date(b[1].created_at || 0);
            return dateB - dateA;
        });
        
        sortedExperiments.forEach(([experimentId, experiment]) => {
            const div = document.createElement('div');
            div.className = 'group-item';
            div.setAttribute('data-experiment', experimentId);
            
            const timeRange = experiment.time_range || {};
            const isCurrent = experiment.is_current || false;
            const startDate = timeRange.start ? new Date(timeRange.start).toLocaleString() : 'Not set';
            const endDate = timeRange.end ? new Date(timeRange.end).toLocaleString() : (isCurrent ? 'Ongoing' : 'Not set');
            
            const linkedGroups = experiment.linked_groups || [];
            const groupCount = linkedGroups.length;
            
            div.innerHTML = `
                <div class="group-header">
                    <h3>${experiment.name || experimentId}${isCurrent ? ' <span style="color: #e74c3c;">(Current)</span>' : ''}</h3>
                    <div class="group-actions">
                        <button onclick="editExperiment('${experimentId}')" class="btn btn-small">Edit</button>
                        <button onclick="deleteExperiment('${experimentId}')" class="btn btn-small btn-danger">Delete</button>
                    </div>
                </div>
                <div class="group-devices">
                    <strong>Description:</strong> ${experiment.description || 'No description'}
                </div>
                <div class="group-devices">
                    <strong>Time Range:</strong> ${startDate} → ${endDate}
                </div>
                <div class="group-devices">
                    <strong>Linked Groups (${groupCount}):</strong>
                    ${groupCount > 0 ? `<ul>${linkedGroups.map(g => `<li>${g}</li>`).join('')}</ul>` : '<p>No groups linked</p>'}
                </div>
                <div class="group-meta">
                    <small>Created: ${experiment.created_at ? new Date(experiment.created_at).toLocaleString() : 'N/A'}</small>
                    ${experiment.updated_at ? `<small style="margin-left: 15px;">Updated: ${new Date(experiment.updated_at).toLocaleString()}</small>` : ''}
                </div>
            `;
            
            container.appendChild(div);
        });
    } catch (error) {
        console.error('Error loading experiments:', error);
        document.getElementById('experimentsList').innerHTML = `<p class="error">Error loading experiments: ${error.message}</p>`;
    }
}

// Delete experiment
async function deleteExperiment(experimentId) {
    if (!confirm(`Are you sure you want to delete experiment "${experimentId}"? This cannot be undone.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/experiments/${encodeURIComponent(experimentId)}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            // Reload experiments list
            await loadExperiments();
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to delete experiment'}`);
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Edit experiment
async function editExperiment(experimentId) {
    try {
        const response = await fetch('/api/experiments');
        const data = await response.json();
        const experiments = data.experiments || {};
        const experiment = experiments[experimentId];
        
        if (!experiment) {
            alert('Experiment not found');
            return;
        }
        
        // Load groups for selection
        const groupsResponse = await fetch('/api/groups');
        const groupsData = await groupsResponse.json();
        const groups = groupsData.groups || {};
        
        // Populate form
        document.getElementById('editExperimentName').textContent = experiment.name || experimentId;
        document.getElementById('editExperimentNameInput').value = experiment.name || experimentId;
        document.getElementById('editExperimentDescription').value = experiment.description || '';
        
        const timeRange = experiment.time_range || {};
        const isCurrent = experiment.is_current || false;
        
        // Format datetime for input fields
        if (timeRange.start) {
            const startDate = new Date(timeRange.start);
            document.getElementById('editExperimentStartTime').value = startDate.toISOString().slice(0, 16);
        }
        if (timeRange.end) {
            const endDate = new Date(timeRange.end);
            document.getElementById('editExperimentEndTime').value = endDate.toISOString().slice(0, 16);
        }
        
        document.getElementById('editExperimentIsCurrent').checked = isCurrent;
        
        // Populate groups checkboxes
        const container = document.getElementById('editExperimentGroups');
        container.innerHTML = '';
        
        const linkedGroups = experiment.linked_groups || [];
        
        for (const [groupName, groupData] of Object.entries(groups)) {
            const label = document.createElement('label');
            label.className = 'checkbox-label';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.name = 'groups';
            checkbox.value = groupName;
            checkbox.checked = linkedGroups.includes(groupName);
            
            const span = document.createElement('span');
            span.textContent = `${groupData.name || groupName} (${(groupData.devices || []).length} device${(groupData.devices || []).length !== 1 ? 's' : ''})`;
            
            label.appendChild(checkbox);
            label.appendChild(span);
            container.appendChild(label);
        }
        
        if (Object.keys(groups).length === 0) {
            container.innerHTML = '<p style="color: #666; font-size: 0.9rem;">No groups found. Please create groups first in "Manage Groups".</p>';
        }
        
        // Store experiment ID for update
        document.getElementById('editExperimentForm').dataset.experimentId = experimentId;
        
        // Show modal
        document.getElementById('editExperimentModal').style.display = 'block';
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Clear end time field
function clearEndTime() {
    document.getElementById('editExperimentEndTime').value = '';
    // Also check the isCurrent checkbox when clearing end time
    document.getElementById('editExperimentIsCurrent').checked = true;
}

// Update experiment
async function updateExperiment(event) {
    event.preventDefault();
    
    const experimentId = document.getElementById('editExperimentForm').dataset.experimentId;
    const name = document.getElementById('editExperimentNameInput').value.trim();
    const description = document.getElementById('editExperimentDescription').value.trim();
    const startTime = document.getElementById('editExperimentStartTime').value;
    const endTime = document.getElementById('editExperimentEndTime').value;
    const isCurrent = document.getElementById('editExperimentIsCurrent').checked;
    
    const checkboxes = document.querySelectorAll('#editExperimentGroups input[type="checkbox"]:checked');
    const linkedGroups = Array.from(checkboxes).map(cb => cb.value).join(',');
    
    try {
        const formData = new FormData();
        formData.append('name', name);
        if (description) formData.append('description', description);
        if (startTime) formData.append('start_time', new Date(startTime).toISOString());
        
        // Handle end_time: if isCurrent is checked, clear it by sending empty string
        // Otherwise, send the endTime value if provided
        if (isCurrent) {
            // Clear end_time to make experiment current again
            formData.append('end_time', '');
        } else if (endTime) {
            formData.append('end_time', new Date(endTime).toISOString());
        }
        
        // Send is_current flag
        formData.append('is_current', isCurrent);
        
        if (linkedGroups) formData.append('linked_groups', linkedGroups);
        
        const response = await fetch(`/api/experiments/${encodeURIComponent(experimentId)}`, {
            method: 'PUT',
            body: formData
        });
        
        if (response.ok) {
            closeEditExperimentModal();
            await loadExperiments();
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to update experiment'}`);
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Close edit modal
function closeEditExperimentModal() {
    document.getElementById('editExperimentModal').style.display = 'none';
}

// Close edit modal when clicking outside (will be overridden in DOMContentLoaded)
function setupModalClickHandlers() {
    // This will be called after DOM loads
}

// Global variable to store groups
let groups = {};

// Load groups
async function loadGroups() {
    try {
        const response = await fetch('/api/groups');
        const data = await response.json();
        groups = data.groups || {};
    } catch (error) {
        console.error('Error loading groups:', error);
    }
}

// Populate group checkboxes for experiment creation
function populateGroupCheckboxes() {
    const container = document.getElementById('experimentGroups');
    if (!container) return;
    
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
        container.innerHTML = '<p style="color: #666; font-size: 0.9rem;">No groups found. Please create groups first in "Groups".</p>';
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
            closeModal('createExperimentModal');
            document.getElementById('createExperimentForm').reset();
            await loadExperiments(); // Reload the experiments list
            alert('Experiment created successfully!');
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to create experiment'}`);
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Update empty state message
async function updateEmptyState() {
    try {
        const response = await fetch('/api/experiments');
        const data = await response.json();
        const experiments = data.experiments || {};
        const container = document.getElementById('experimentsList');
        if (container && Object.keys(experiments).length === 0) {
            container.innerHTML = '<p class="empty-state">No experiments created yet. Click "Create Experiment" above to get started!</p>';
        }
    } catch (error) {
        // Ignore errors here
    }
}

// Load experiments on page load
document.addEventListener('DOMContentLoaded', async () => {
    await loadGroups(); // Load groups first
    await loadExperiments(); // Then load experiments
    updateEmptyState(); // Update empty state message
    
    // Set up create experiment button
    const createBtn = document.getElementById('createExperimentBtn');
    if (createBtn) {
        createBtn.addEventListener('click', () => {
            populateGroupCheckboxes(); // Populate groups when opening modal
            openModal('createExperimentModal');
        });
    }
    
    // Close modal when clicking outside
    document.addEventListener('click', function(event) {
        const createModal = document.getElementById('createExperimentModal');
        const editModal = document.getElementById('editExperimentModal');
        if (event.target === createModal) {
            closeModal('createExperimentModal');
        }
        if (event.target === editModal) {
            closeEditExperimentModal();
        }
    });
});

