// queue_management.js

// ===== GLOBALS =====
let currentDeleteId = null;
let currentDeleteBooked = 0;
let pendingForceDelete = false;
let currentFilter = 'all';
let currentSearch = '';
let refreshInterval = null;
let isRefreshing = false;

// ===== REAL-TIME DATA FETCHING =====

// Start auto-refresh (every 5 seconds)
function startAutoRefresh() {
    if (refreshInterval) clearInterval(refreshInterval);
    
    refreshInterval = setInterval(() => {
        refreshQueueData();
    }, 5000); // Refresh every 5 seconds
    console.log('Auto-refresh started - refreshing every 5 seconds');
}

// Stop auto-refresh
function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
        console.log('Auto-refresh stopped');
    }
}

// Fetch fresh data from server
async function refreshQueueData() {
    if (isRefreshing) return;
    isRefreshing = true;
    
    console.log('Refreshing queue data...');
    
    try {
        const response = await fetch('/api/get-queues-data');
        const data = await response.json();
        
        if (data.success) {
            // Update TOKEN_MAP with new data
            updateTokenMap(data.queues);
            // Update table with new data
            updateTableWithNewData(data.queues);
            // Update stats
            updateStatsFromData(data.queues);
            
            // Update the live indicator
            const livePill = document.querySelector('.live-pill');
            if (livePill) {
                livePill.style.opacity = '0.7';
                setTimeout(() => {
                    if (livePill) livePill.style.opacity = '1';
                }, 200);
            }
            
            console.log('Data refreshed successfully');
        }
    } catch (error) {
        console.error('Error refreshing data:', error);
    } finally {
        isRefreshing = false;
    }
}

// Update TOKEN_MAP with new data
function updateTokenMap(queues) {
    window.TOKEN_MAP = {};
    queues.forEach(q => {
        if (q.tokens && q.tokens.length > 0) {
            window.TOKEN_MAP[q.id] = q.tokens;
        } else {
            window.TOKEN_MAP[q.id] = [];
        }
    });
}

// Update table with new data
function updateTableWithNewData(queues) {
    const tbody = document.querySelector('#queueTable tbody');
    if (!tbody) return;
    
    // Clear existing rows (except empty state)
    const existingRows = tbody.querySelectorAll('tr:not(.empty-state-row)');
    existingRows.forEach(row => row.remove());
    
    if (queues.length === 0) {
        // Show empty state
        if (!tbody.querySelector('.empty-state-row')) {
            const emptyRow = document.createElement('tr');
            emptyRow.className = 'empty-state-row';
            emptyRow.innerHTML = `<td colspan="8">
                <div class="empty-state">
                    <i class="fa-solid fa-layer-group"></i>
                    <p>No queues found. Create your first queue to get started.</p>
                </div>
            </td>`;
            tbody.appendChild(emptyRow);
        }
        return;
    }
    
    // Remove empty state if exists
    const emptyStateRow = tbody.querySelector('.empty-state-row');
    if (emptyStateRow) emptyStateRow.remove();
    
    // Add new rows
    queues.forEach(q => {
        const row = createQueueRow(q);
        tbody.appendChild(row);
    });
    
    // Reapply current filters
    applyFilters();
}

// Create a table row from queue data
function createQueueRow(q) {
    const row = document.createElement('tr');
    row.id = `row_${q.id}`;
    row.setAttribute('data-status', q.status);
    row.setAttribute('data-name', q.name.toLowerCase());
    
    // Queue Name cell
    const nameCell = document.createElement('td');
    nameCell.innerHTML = `
        <div class="queue-name-cell">
            <span class="queue-name">${escapeHtml(q.name)}</span>
            <span class="queue-id">#${q.id}</span>
        </div>
    `;
    row.appendChild(nameCell);
    
    // Type cell
    const typeCell = document.createElement('td');
    typeCell.innerHTML = `<span class="type-badge ${q.type}">${q.type.charAt(0).toUpperCase() + q.type.slice(1)}</span>`;
    row.appendChild(typeCell);
    
    // Limit cell
    const limitCell = document.createElement('td');
    limitCell.innerHTML = `
        <span class="limit-num">${q.max}</span>
        <span class="limit-sub">per day</span>
    `;
    row.appendChild(limitCell);
    
    // Counter cell
    const counterCell = document.createElement('td');
    if (q.counter_name) {
        counterCell.innerHTML = `<span class="counter-pill"><i class="fa-solid fa-desktop"></i> ${escapeHtml(q.counter_name)}</span>`;
    } else {
        counterCell.innerHTML = `<span class="counter-none">—</span>`;
    }
    row.appendChild(counterCell);
    
    // Booked cell
    const bookedCell = document.createElement('td');
    bookedCell.innerHTML = `<span class="booked-val" id="booked_${q.id}">${q.booked}</span>`;
    row.appendChild(bookedCell);
    
    // Active Tokens cell
    const tokensCell = document.createElement('td');
    if (q.tokens && q.tokens.length > 0) {
        tokensCell.innerHTML = `
            <button class="view-tokens-btn" onclick="openTokenModal('${q.id}')">
                <i class="fa-solid fa-ticket"></i>
                ${q.tokens.length} token${q.tokens.length !== 1 ? 's' : ''}
            </button>
        `;
    } else {
        tokensCell.innerHTML = `<span class="no-tokens">No active tokens</span>`;
    }
    row.appendChild(tokensCell);
    
    // Status cell
    const statusCell = document.createElement('td');
    statusCell.innerHTML = `
        <span class="status-badge ${q.status}">
            <span class="sdot"></span>${q.status.charAt(0).toUpperCase() + q.status.slice(1)}
        </span>
    `;
    row.appendChild(statusCell);
    
    // Actions cell
    const actionsCell = document.createElement('td');
    actionsCell.innerHTML = `
        <div class="tbl-actions">
            <button class="icon-btn edit" title="Edit" onclick="openEditModal('${q.id}')">
                <i class="fa-solid fa-pen"></i>
            </button>
            <button class="icon-btn del" title="Delete"
                onclick="deleteQueue(this)"
                data-id="${q.id}"
                data-booked="${q.booked}">
                <i class="fa-solid fa-trash"></i>
            </button>
        </div>
    `;
    row.appendChild(actionsCell);
    
    return row;
}

// Update stats from API data
function updateStatsFromData(queues) {
    const totalQueues = queues.length;
    const activeQueues = queues.filter(q => q.status === 'active').length;
    const inactiveQueues = queues.filter(q => q.status === 'inactive').length;
    const totalTokens = queues.reduce((sum, q) => sum + (q.booked || 0), 0);
    
    const statValues = document.querySelectorAll('.stat-value');
    if (statValues[0]) statValues[0].textContent = totalQueues;
    if (statValues[1]) statValues[1].textContent = activeQueues;
    if (statValues[2]) statValues[2].textContent = inactiveQueues;
    if (statValues[3]) statValues[3].textContent = totalTokens;
    
    // Update tab counts
    const tabCounts = document.querySelectorAll('.tab-count');
    if (tabCounts[0]) tabCounts[0].textContent = totalQueues;
    if (tabCounts[1]) tabCounts[1].textContent = activeQueues;
    if (tabCounts[2]) tabCounts[2].textContent = inactiveQueues;
}

// ===== FILTER & SEARCH =====
function filterTable(status, btnElement) {
    currentFilter = status;
    
    // Update active tab styling
    document.querySelectorAll('.ftab').forEach(btn => {
        btn.classList.remove('active');
    });
    if (btnElement) {
        btnElement.classList.add('active');
    } else {
        const tabs = document.querySelectorAll('.ftab');
        let targetTab = null;
        if (status === 'all') targetTab = tabs[0];
        else if (status === 'active') targetTab = tabs[1];
        else if (status === 'inactive') targetTab = tabs[2];
        if (targetTab) targetTab.classList.add('active');
    }
    
    applyFilters();
}

function searchTable() {
    const searchInput = document.getElementById('searchInput');
    currentSearch = searchInput ? searchInput.value.toLowerCase() : '';
    applyFilters();
}

function applyFilters() {
    const tableRows = document.querySelectorAll('#queueTable tbody tr');
    let visibleCount = 0;
    
    tableRows.forEach(row => {
        if (row.querySelector('.empty-state')) {
            row.style.display = '';
            return;
        }
        
        const status = row.getAttribute('data-status') || '';
        const name = row.getAttribute('data-name') || '';
        
        let statusMatch = false;
        if (currentFilter === 'all') statusMatch = true;
        else if (currentFilter === 'active') statusMatch = (status === 'active');
        else if (currentFilter === 'inactive') statusMatch = (status === 'inactive');
        
        const searchMatch = currentSearch === '' || name.includes(currentSearch);
        
        if (statusMatch && searchMatch) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });
    
    const showingSpan = document.getElementById('showing-count');
    if (showingSpan) showingSpan.textContent = visibleCount;
    
    const tbody = document.querySelector('#queueTable tbody');
    const hasVisibleRows = visibleCount > 0;
    const emptyStateRow = tbody ? tbody.querySelector('.empty-state-row') : null;
    
    if (!hasVisibleRows && !emptyStateRow) {
        const emptyRow = document.createElement('tr');
        emptyRow.className = 'empty-state-row';
        emptyRow.innerHTML = `<td colspan="8">
            <div class="empty-state">
                <i class="fa-solid fa-filter"></i>
                <p>No queues match your filters</p>
            </div>
        </td>`;
        if (tbody) tbody.appendChild(emptyRow);
    } else if (hasVisibleRows && emptyStateRow) {
        emptyStateRow.remove();
    }
}

// ===== TOAST NOTIFICATION =====
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    toast.textContent = message;
    toast.className = `toast t-${type}`;
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// ===== EDIT MODAL FUNCTIONS =====
function openEditModal(queueId) {
    const row = document.getElementById(`row_${queueId}`);
    if (!row) {
        showToast('Queue not found', 'error');
        return;
    }
    
    const nameCell = row.cells[0];
    const nameSpan = nameCell ? nameCell.querySelector('.queue-name') : null;
    const queueName = nameSpan ? nameSpan.textContent : '';
    
    const typeSpan = row.cells[1] ? row.cells[1].querySelector('.type-badge') : null;
    let queueType = typeSpan ? typeSpan.textContent.toLowerCase() : 'medium';
    queueType = queueType === 'short' ? 'short' : (queueType === 'long' ? 'long' : 'medium');
    
    const limitSpan = row.cells[2] ? row.cells[2].querySelector('.limit-num') : null;
    const maxLimit = limitSpan ? parseInt(limitSpan.textContent) : 50;
    
    const counterSpan = row.cells[3] ? row.cells[3].querySelector('.counter-pill') : null;
    let counterId = '';
    if (counterSpan && counterSpan.textContent) {
        const counterText = counterSpan.textContent.replace(/[^a-zA-Z0-9\s]/g, '').trim();
        const counterSelect = document.getElementById('edit-counter');
        if (counterSelect) {
            for (let i = 0; i < counterSelect.options.length; i++) {
                if (counterSelect.options[i].text.includes(counterText)) {
                    counterId = counterSelect.options[i].value;
                    break;
                }
            }
        }
    }
    
    const statusSpan = row.cells[6] ? row.cells[6].querySelector('.status-badge') : null;
    let statusClass = 'inactive';
    if (statusSpan) {
        statusClass = statusSpan.classList.contains('active') ? 'active' : 'inactive';
    }
    
    document.getElementById('edit-id').value = queueId;
    document.getElementById('edit-name').value = queueName;
    document.getElementById('edit-type').value = queueType;
    document.getElementById('edit-max').textContent = maxLimit;
    
    const counterSelect = document.getElementById('edit-counter');
    if (counterSelect) counterSelect.value = counterId;
    
    const statusCheck = document.getElementById('edit-status-check');
    if (statusCheck) statusCheck.checked = (statusClass === 'active');
    
    const modal = document.getElementById('editModal');
    if (modal) modal.classList.add('show');
}

function closeEditModal() {
    const modal = document.getElementById('editModal');
    if (modal) modal.classList.remove('show');
}

function changeEditMax(delta) {
    const maxSpan = document.getElementById('edit-max');
    if (!maxSpan) return;
    let current = parseInt(maxSpan.textContent) || 50;
    let newVal = current + delta;
    if (newVal < 1) newVal = 1;
    if (newVal > 999) newVal = 999;
    maxSpan.textContent = newVal;
}

function saveQueueModal() {
    const queueId = document.getElementById('edit-id').value;
    const name = document.getElementById('edit-name').value;
    const type = document.getElementById('edit-type').value;
    const max = parseInt(document.getElementById('edit-max').textContent);
    const counter = document.getElementById('edit-counter').value;
    const statusCheck = document.getElementById('edit-status-check');
    const status = statusCheck && statusCheck.checked ? 'active' : 'inactive';
    
    if (!name.trim()) {
        showToast('Queue name is required', 'error');
        return;
    }
    
    const saveBtn = document.querySelector('#editModal .btn-save-modal');
    const originalText = saveBtn ? saveBtn.innerHTML : '';
    if (saveBtn) {
        saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
        saveBtn.disabled = true;
    }
    
    fetch('/update-queue', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            id: queueId,
            name: name,
            type: type,
            max: max,
            counter: counter || null,
            status: status
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            refreshQueueData(); // Refresh after update
            showToast('Queue updated successfully', 'success');
            closeEditModal();
        } else {
            showToast('Failed to update queue', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('An error occurred', 'error');
    })
    .finally(() => {
        if (saveBtn) {
            saveBtn.innerHTML = originalText;
            saveBtn.disabled = false;
        }
    });
}

function updateTableRow(queueId, name, type, max, counterId, status) {
    const row = document.getElementById(`row_${queueId}`);
    if (!row) return;
    
    row.setAttribute('data-status', status);
    row.setAttribute('data-name', name.toLowerCase());
    
    const nameCell = row.cells[0];
    if (nameCell) {
        nameCell.innerHTML = `
            <div class="queue-name-cell">
                <span class="queue-name">${escapeHtml(name)}</span>
                <span class="queue-id">#${queueId}</span>
            </div>
        `;
    }
    
    const typeCell = row.cells[1];
    if (typeCell) {
        typeCell.innerHTML = `<span class="type-badge ${type}">${type.charAt(0).toUpperCase() + type.slice(1)}</span>`;
    }
    
    const limitCell = row.cells[2];
    if (limitCell) {
        limitCell.innerHTML = `
            <span class="limit-num">${max}</span>
            <span class="limit-sub">per day</span>
        `;
    }
    
    const counterCell = row.cells[3];
    if (counterCell) {
        let counterName = '';
        const counterSelect = document.getElementById('edit-counter');
        if (counterSelect && counterId) {
            const option = counterSelect.querySelector(`option[value="${counterId}"]`);
            if (option) counterName = option.textContent;
        }
        
        if (counterName) {
            counterCell.innerHTML = `<span class="counter-pill"><i class="fa-solid fa-desktop"></i> ${escapeHtml(counterName)}</span>`;
        } else {
            counterCell.innerHTML = `<span class="counter-none">—</span>`;
        }
    }
    
    const statusCell = row.cells[6];
    if (statusCell) {
        statusCell.innerHTML = `
            <span class="status-badge ${status}">
                <span class="sdot"></span>${status.charAt(0).toUpperCase() + status.slice(1)}
            </span>
        `;
    }
    
    const delBtn = row.querySelector('.icon-btn.del');
    if (delBtn) {
        delBtn.setAttribute('data-id', queueId);
    }
    
    applyFilters();
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== DELETE QUEUE FUNCTIONS =====
function deleteQueue(btnElement) {
    const queueId = btnElement.getAttribute('data-id');
    const booked = parseInt(btnElement.getAttribute('data-booked')) || 0;
    
    currentDeleteId = queueId;
    currentDeleteBooked = booked;
    
    if (booked > 0) {
        const modal = document.getElementById('deleteModal');
        if (modal) modal.classList.add('show');
    } else {
        performDelete(queueId, false);
    }
}

function closeModal() {
    const modal = document.getElementById('deleteModal');
    if (modal) modal.classList.remove('show');
    currentDeleteId = null;
    currentDeleteBooked = 0;
}

function forceDelete() {
    if (currentDeleteId) {
        closeModal();
        performDelete(currentDeleteId, true);
    }
}

function performDelete(queueId, force) {
    const delBtn = document.querySelector(`#row_${queueId} .icon-btn.del`);
    if (delBtn) {
        delBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        delBtn.disabled = true;
    }
    
    fetch('/delete-queue', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            id: queueId,
            force: force
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            refreshQueueData(); // Refresh after delete
            showToast('Queue deleted successfully', 'success');
        } else if (data.error === 'HAS_BOOKINGS') {
            showToast('Queue has active bookings. Use force delete to remove.', 'error');
            const modal = document.getElementById('deleteModal');
            if (modal) modal.classList.add('show');
        } else {
            showToast('Failed to delete queue', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('An error occurred', 'error');
    })
    .finally(() => {
        if (delBtn) {
            delBtn.innerHTML = '<i class="fa-solid fa-trash"></i>';
            delBtn.disabled = false;
        }
    });
}

function updateStats() {
    const rows = document.querySelectorAll('#queueTable tbody tr:not(.empty-state-row)');
    let totalQueues = 0;
    let activeQueues = 0;
    let inactiveQueues = 0;
    let totalTokens = 0;
    
    rows.forEach(row => {
        if (row.querySelector('.empty-state')) return;
        totalQueues++;
        
        const status = row.getAttribute('data-status');
        if (status === 'active') activeQueues++;
        if (status === 'inactive') inactiveQueues++;
        
        const bookedSpan = row.querySelector('.booked-val');
        if (bookedSpan) {
            totalTokens += parseInt(bookedSpan.textContent) || 0;
        }
    });
    
    const statValues = document.querySelectorAll('.stat-value');
    if (statValues[0]) statValues[0].textContent = totalQueues;
    if (statValues[1]) statValues[1].textContent = activeQueues;
    if (statValues[2]) statValues[2].textContent = inactiveQueues;
    if (statValues[3]) statValues[3].textContent = totalTokens;
    
    const tabCounts = document.querySelectorAll('.tab-count');
    if (tabCounts[0]) tabCounts[0].textContent = totalQueues;
    if (tabCounts[1]) tabCounts[1].textContent = activeQueues;
    if (tabCounts[2]) tabCounts[2].textContent = inactiveQueues;
}

// ===== TOKEN MODAL FUNCTIONS =====
function openTokenModal(queueId) {
    const tokens = window.TOKEN_MAP ? window.TOKEN_MAP[queueId] || [] : [];
    const modalBody = document.getElementById('tokenModalBody');
    
    if (!modalBody) return;
    
    if (tokens.length === 0) {
        modalBody.innerHTML = '<p style="text-align:center; color:var(--text-muted);">No active tokens in this queue.</p>';
    } else {
        let html = '<div class="token-list-modal">';
        tokens.forEach(token => {
            html += `
                <div class="token-detail-row" id="token-row-${token.id}">
                    <div>
                        <div class="token-detail-num">${escapeHtml(token.number)}</div>
                        <div class="token-detail-svc">${escapeHtml(token.service || 'General Service')}</div>
                        <div class="token-detail-time">${escapeHtml(token.time || 'No time')}</div>
                    </div>
                    <button class="t-del-modal" onclick="deleteToken('${token.id}', '${queueId}')" title="Remove token">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            `;
        });
        html += '</div>';
        modalBody.innerHTML = html;
    }
    
    const modal = document.getElementById('tokenModal');
    if (modal) modal.classList.add('show');
}

function closeTokenModal() {
    const modal = document.getElementById('tokenModal');
    if (modal) modal.classList.remove('show');
}

function deleteToken(tokenId, queueId) {
    fetch('/delete-token', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: tokenId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            refreshQueueData(); // Refresh after token deletion
            showToast('Token removed successfully', 'success');
            closeTokenModal();
        } else {
            showToast('Failed to remove token', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('An error occurred', 'error');
    });
}

// ===== MODAL CLOSE ON OUTSIDE CLICK =====
document.addEventListener('click', function(event) {
    const editModal = document.getElementById('editModal');
    if (editModal && editModal.classList.contains('show')) {
        if (event.target === editModal) {
            closeEditModal();
        }
    }
    
    const deleteModal = document.getElementById('deleteModal');
    if (deleteModal && deleteModal.classList.contains('show')) {
        if (event.target === deleteModal) {
            closeModal();
        }
    }
    
    const tokenModal = document.getElementById('tokenModal');
    if (tokenModal && tokenModal.classList.contains('show')) {
        if (event.target === tokenModal) {
            closeTokenModal();
        }
    }
});

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('Queue Management Page Loaded');
    updateStats();
    startAutoRefresh(); // Start auto-refresh every 5 seconds
    console.log('Auto-refresh is active - data will update every 5 seconds');
    
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeEditModal();
            closeModal();
            closeTokenModal();
        }
    });
});

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    stopAutoRefresh();
});