// Experiments management functions

function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function experimentState(experiment) {
    // Returns {state: 'running'|'completed'|'draft'|'stopped', label, cssClass}
    const tr = experiment.time_range || {};
    const isCurrent = !!experiment.is_current;
    if (isCurrent) {
        return { state: 'running',   label: '▶ Running',   cssClass: 'state-running' };
    }
    if (tr.start && tr.end) {
        return { state: 'completed', label: '✓ Completed', cssClass: 'state-completed' };
    }
    if (tr.start && !tr.end) {
        // Has a start but no end and not current — orphan state from the legacy flow.
        return { state: 'stopped',   label: '⏸ Stopped',   cssClass: 'state-stopped' };
    }
    return { state: 'draft', label: '· Draft', cssClass: 'state-draft' };
}

async function fetchCollectorStatus() {
    try {
        const r = await fetch('/api/collector/status');
        if (!r.ok) return null;
        return await r.json();
    } catch (_) { return null; }
}

async function renderRunningPanel(experiments) {
    const panel = document.getElementById('runningPanel');
    if (!panel) return;
    const running = Object.entries(experiments).filter(([_, e]) => e.is_current);

    if (running.length === 0) {
        panel.innerHTML = `
            <div class="running-panel running-panel-empty">
                <div class="running-icon">○</div>
                <div class="running-body">
                    <div class="running-title">No experiment is currently running.</div>
                    <div class="running-sub">Start one from the list below — or use <strong>Create Experiment</strong> to define a new one.</div>
                </div>
            </div>
        `;
        return;
    }

    // Pull system status once so we can render the focus health pill (if active).
    const status = await fetchCollectorStatus();
    const systemFocusLevel = status ? (status.focus_level || 0) : 0;
    const focusTelem = (status && status.runtime && status.runtime.focus) || null;

    panel.innerHTML = running.map(([id, e]) => {
        const tr = e.time_range || {};
        const startedAt = tr.start ? new Date(tr.start) : null;
        const startedTxt = startedAt ? startedAt.toLocaleString() : 'unknown';
        const elapsedTxt = startedAt ? humanElapsed(Date.now() - startedAt.getTime()) : '';
        const groupCount = (e.linked_groups || []).length;

        // Focus block — system focus is on AND this experiment is the one being focused
        let focusBlock = '';
        if (systemFocusLevel === 2) {
            const tick = e.target_cadence_s || 10;
            let pillHtml = '';
            let detailHtml = '';
            const matchesThis = focusTelem && focusTelem.active && focusTelem.experiment_id === id;
            if (matchesThis) {
                const health = focusTelem.health || 'unknown';
                const lastRound = focusTelem.last_round_s != null ? focusTelem.last_round_s.toFixed(2) : '?';
                const utilPct = focusTelem.tick_utilization_pct != null ? focusTelem.tick_utilization_pct.toFixed(0) : '?';
                pillHtml = `<span class="health-pill health-${health}" title="Round time as % of tick">● ${health.toUpperCase()}</span>`;
                detailHtml = `last round ${lastRound}s · ${utilPct}% of ${tick}s tick · ${focusTelem.device_count} device${focusTelem.device_count === 1 ? '' : 's'}`;
            } else {
                pillHtml = `<span class="health-pill health-unknown">● starting…</span>`;
                detailHtml = `Strong focus · preferred cadence ${tick}s · waiting for first cycle`;
            }
            focusBlock = `
                <div class="running-focus">
                    <span class="focus-tag">STRONG FOCUS</span>
                    ${pillHtml}
                    <span class="focus-detail">${escapeHtml(detailHtml)}</span>
                </div>
            `;
        }

        return `
            <div class="running-panel running-panel-active">
                <div class="running-icon">▶</div>
                <div class="running-body">
                    <div class="running-title">${escapeHtml(e.name || id)}</div>
                    <div class="running-sub">Started ${escapeHtml(startedTxt)}${elapsedTxt ? ' · running ' + escapeHtml(elapsedTxt) : ''} · ${groupCount} group${groupCount === 1 ? '' : 's'}</div>
                    ${focusBlock}
                </div>
                <div class="running-actions">
                    <button class="btn btn-danger" onclick="stopExperiment('${escapeHtml(id)}')">⏹ Stop experiment</button>
                </div>
            </div>
        `;
    }).join('');
}

// Refresh focus telemetry every 5s while a focus experiment is running.
setInterval(async () => {
    const panel = document.getElementById('runningPanel');
    if (!panel || !panel.querySelector('.running-focus')) return;
    try {
        const r = await fetch('/api/experiments');
        if (!r.ok) return;
        const data = await r.json();
        renderRunningPanel(data.experiments || {});
    } catch (_) { /* ignore */ }
}, 5000);

function humanElapsed(ms) {
    const sec = Math.floor(ms / 1000);
    if (sec < 60) return `${sec}s`;
    const min = Math.floor(sec / 60);
    if (min < 60) return `${min} min`;
    const hr = Math.floor(min / 60);
    if (hr < 48) return `${hr} h ${min % 60} min`;
    const d = Math.floor(hr / 24);
    return `${d} d ${hr % 24} h`;
}

// Load and display experiments
async function loadExperiments() {
    try {
        const response = await fetch('/api/experiments');
        const data = await response.json();
        const experiments = data.experiments || {};

        renderRunningPanel(experiments);

        const container = document.getElementById('experimentsList');

        if (Object.keys(experiments).length === 0) {
            container.innerHTML = '<p class="empty-state">No experiments created yet. Click "Create Experiment" above to get started!</p>';
            return;
        }

        container.innerHTML = '';

        // Sort: running first, then by creation date (newest first)
        const sortedExperiments = Object.entries(experiments).sort((a, b) => {
            const aRunning = a[1].is_current ? 0 : 1;
            const bRunning = b[1].is_current ? 0 : 1;
            if (aRunning !== bRunning) return aRunning - bRunning;
            const dateA = new Date(a[1].created_at || 0);
            const dateB = new Date(b[1].created_at || 0);
            return dateB - dateA;
        });

        sortedExperiments.forEach(([experimentId, experiment]) => {
            const div = document.createElement('div');
            div.className = 'group-item';
            div.setAttribute('data-experiment', experimentId);

            const timeRange = experiment.time_range || {};
            const status = experimentState(experiment);
            const startDate = timeRange.start ? new Date(timeRange.start).toLocaleString() : 'Not set';
            const endDate = timeRange.end ? new Date(timeRange.end).toLocaleString() : (status.state === 'running' ? 'Ongoing' : 'Not set');

            const linkedGroups = experiment.linked_groups || [];
            const groupCount = linkedGroups.length;

            // Action buttons depend on state
            let stateActions = '';
            if (status.state === 'running') {
                stateActions = `<button onclick="stopExperiment('${escapeHtml(experimentId)}')" class="btn btn-small btn-danger" title="End this experiment">⏹ Stop</button>`;
            } else if (status.state === 'draft' || status.state === 'stopped') {
                stateActions = `<button onclick="startExperiment('${escapeHtml(experimentId)}')" class="btn btn-small btn-primary" title="Start this experiment now">▶ Start</button>`;
            } else if (status.state === 'completed') {
                stateActions = `<button onclick="startExperiment('${escapeHtml(experimentId)}')" class="btn btn-small" title="Re-run this experiment (clears existing end time)">▶ Re-start</button>`;
            }

            div.innerHTML = `
                <div class="group-header">
                    <h3>
                        <span class="experiment-state ${status.cssClass}">${status.label}</span>
                        ${escapeHtml(experiment.name || experimentId)}
                    </h3>
                    <div class="group-actions">
                        ${stateActions}
                        <button type="button" onclick="showJoinCode('${escapeHtml(experimentId)}')" class="btn btn-small" title="Generate a LEM join code so volunteers can stream local measurements into this experiment">🔌 LEM join code</button>
                        <button type="button" onclick="downloadExperimentExport(event, '${escapeHtml(experimentId)}')" class="btn btn-small" title="ZIP: raw power readings (every poll), metadata, annotations">Download all data</button>
                        <button onclick="editExperiment('${escapeHtml(experimentId)}')" class="btn btn-small">Edit</button>
                        <button onclick="deleteExperiment('${escapeHtml(experimentId)}')" class="btn btn-small btn-danger">Delete</button>
                    </div>
                </div>
                <div class="group-devices">
                    <strong>Description:</strong> ${escapeHtml(experiment.description || 'No description')}
                </div>
                <div class="group-devices">
                    <strong>Time Range:</strong> ${escapeHtml(startDate)} → ${escapeHtml(endDate)}
                </div>
                <div class="group-devices">
                    <strong>Linked Groups (${groupCount}):</strong>
                    ${groupCount > 0 ? `<ul>${linkedGroups.map(g => `<li>${escapeHtml(g)}</li>`).join('')}</ul>` : '<p>No groups linked</p>'}
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

// ----------------------------------------------------------------------------
// Start / Stop — single source of truth, server enforces single-running invariant
// ----------------------------------------------------------------------------

async function startExperiment(experimentId) {
    // Look up how many other experiments are currently running so we can warn the operator
    let confirmMsg = `Start experiment "${experimentId}"?`;
    try {
        const response = await fetch('/api/experiments');
        const data = await response.json();
        const experiments = data.experiments || {};
        const target = experiments[experimentId] || {};
        const otherRunning = Object.entries(experiments).filter(([id, e]) => id !== experimentId && e.is_current);

        if (otherRunning.length > 0) {
            const names = otherRunning.map(([_, e]) => `"${e.name || _}"`).join(', ');
            confirmMsg = `Start "${target.name || experimentId}"?\n\nThis will automatically stop the currently-running experiment: ${names}.\n\nOnly one experiment runs at a time.`;
        } else if (target.time_range && target.time_range.start && target.time_range.end) {
            confirmMsg = `Re-start "${target.name || experimentId}"?\n\nThis is a Completed experiment. Re-starting will clear its existing end time and stamp a fresh start time of now.`;
        } else {
            confirmMsg = `Start "${target.name || experimentId}"?`;
        }
    } catch (e) { /* fall through to default confirm */ }

    if (!confirm(confirmMsg)) return;

    try {
        const response = await fetch(`/api/experiments/${encodeURIComponent(experimentId)}/start`, { method: 'POST' });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            alert(`Failed to start: ${err.detail || response.statusText}`);
            return;
        }
        loadExperiments();
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

async function stopExperiment(experimentId) {
    if (!confirm(`Stop experiment "${experimentId}"?`)) return;
    try {
        const response = await fetch(`/api/experiments/${encodeURIComponent(experimentId)}/end`, { method: 'POST' });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            alert(`Failed to stop: ${err.detail || response.statusText}`);
            return;
        }
        loadExperiments();
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

// Generate and show a LEM join code (short + long) for an experiment.
async function showJoinCode(experimentId) {
    try {
        const r = await fetch(`/api/experiments/${encodeURIComponent(experimentId)}/field-token`, { method: 'POST' });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const d = await r.json();
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;z-index:9999';
        overlay.innerHTML = `
            <div style="background:#fff;color:#222;padding:24px;border-radius:8px;max-width:520px;font-family:sans-serif">
                <h3 style="margin-top:0">LEM join code — ${escapeHtml(experimentId)}</h3>
                <p>Volunteers type this short code into LEM (<code>lem rem join …</code> or the Connect to REM dialog):</p>
                <div style="font-size:2em;font-weight:bold;letter-spacing:3px;text-align:center;padding:10px;background:#f2f2f2;border-radius:6px">${escapeHtml(d.short_code || '')}</div>
                <p style="margin-top:14px;font-size:.9em;color:#666">Full code (works without setting a server URL):</p>
                <textarea readonly style="width:100%;height:52px;font-size:.75em" onclick="this.select()">${escapeHtml(d.join_code || '')}</textarea>
                <p style="font-size:.85em;color:#a00">Generating a new code replaces any previous one for this experiment.</p>
                <div style="text-align:right"><button class="btn" onclick="this.closest('div').parentNode.remove()">Close</button></div>
            </div>`;
        overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
        document.body.appendChild(overlay);
    } catch (e) {
        alert('Could not generate join code: ' + e.message);
    }
}

// Make these globally accessible for inline onclick handlers
window.startExperiment = startExperiment;
window.stopExperiment = stopExperiment;
window.showJoinCode = showJoinCode;

// Download full experiment data (raw DB readings + metadata ZIP)
async function downloadExperimentExport(ev, experimentId) {
    const btn = ev && ev.target;
    if (btn && btn.disabled) return;
    const prev = btn ? btn.textContent : '';
    try {
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Preparing…';
        }
        const url = `/api/experiments/${encodeURIComponent(experimentId)}/export`;
        const response = await fetch(url);
        if (!response.ok) {
            let detail = response.statusText;
            try {
                const err = await response.json();
                detail = err.detail || detail;
            } catch (e) {
                /* ignore */
            }
            throw new Error(detail);
        }
        const cd = response.headers.get('Content-Disposition');
        let filename = `experiment-${experimentId}-export.zip`;
        if (cd && cd.includes('filename=')) {
            const m = cd.match(/filename="?([^";]+)"?/);
            if (m) filename = m[1].trim();
        }
        const blob = await response.blob();
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(a.href);
    } catch (e) {
        alert(`Export failed: ${e.message || e}`);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = prev;
        }
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
        
        const focusTick = document.getElementById('editExperimentTargetCadence');
        if (focusTick) {
            focusTick.value = experiment.target_cadence_s || 10;
        }

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
    // Just clear the date field. Lifecycle is changed via Start/Stop buttons,
    // not by side-effect of editing date fields.
    document.getElementById('editExperimentEndTime').value = '';
}

// Update experiment — metadata only. Lifecycle (running/stopped) is changed via
// the Start/Stop buttons on the experiment card, not from this dialog.
async function updateExperiment(event) {
    event.preventDefault();

    const experimentId = document.getElementById('editExperimentForm').dataset.experimentId;
    const name = document.getElementById('editExperimentNameInput').value.trim();
    const description = document.getElementById('editExperimentDescription').value.trim();
    const startTime = document.getElementById('editExperimentStartTime').value;
    const endTime = document.getElementById('editExperimentEndTime').value;

    const checkboxes = document.querySelectorAll('#editExperimentGroups input[type="checkbox"]:checked');
    const linkedGroups = Array.from(checkboxes).map(cb => cb.value).join(',');

    const editTargetCadence = parseInt(document.getElementById('editExperimentTargetCadence').value, 10) || 10;

    try {
        const formData = new FormData();
        formData.append('name', name);
        if (description) formData.append('description', description);
        if (startTime) formData.append('start_time', new Date(startTime).toISOString());
        // End time: pass through empty string (which the backend interprets as "clear")
        // or an ISO string. We do NOT touch is_current — that's owned by Start/Stop.
        formData.append('end_time', endTime ? new Date(endTime).toISOString() : '');
        if (linkedGroups) formData.append('linked_groups', linkedGroups);
        formData.append('target_cadence_s', String(editTargetCadence));

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
    const targetCadence = parseInt(document.getElementById('experimentTargetCadence').value, 10) || 10;
    const checkboxes = document.querySelectorAll('#experimentGroups input[type="checkbox"]:checked');
    const selectedGroups = Array.from(checkboxes).map(cb => cb.value);

    if (selectedGroups.length === 0) {
        alert('Please select at least one participant group');
        return;
    }

    // Two valid create shapes:
    //   (a) Both times blank → Draft (operator clicks ▶ Start when ready)
    //   (b) Both times set → retrospective Completed experiment
    // Mixing one and not the other is rejected.
    if (Boolean(startTime) !== Boolean(endTime)) {
        alert('Either set both start AND end times (retrospective experiment), or leave both blank (Draft — start later with ▶ Start).');
        return;
    }

    try {
        const formData = new FormData();
        formData.append('name', name);
        formData.append('description', description || '');
        if (startTime) formData.append('start_time', new Date(startTime).toISOString());
        if (endTime)   formData.append('end_time',   new Date(endTime).toISOString());
        // is_current is no longer set at creation time — it's only set by /start.
        // Send false explicitly so the backend never accidentally creates as running.
        formData.append('is_current', 'false');
        formData.append('linked_groups', selectedGroups.join(','));
        formData.append('target_cadence_s', String(targetCadence));

        const response = await fetch('/api/experiments', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            closeModal('createExperimentModal');
            document.getElementById('createExperimentForm').reset();
            await loadExperiments();
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
            const tick = document.getElementById('experimentTargetCadence');
            if (tick) tick.value = 10;
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

