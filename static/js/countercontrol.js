// Counter Control JS
let currentCounterId = null;
let currentTokenIdForArrival = null;
let pendingAction = null;
let pendingActionData = null;

// DOM Elements
const countersListEl = document.getElementById('countersList');
const noCounterDiv = document.getElementById('noCounterSelected');
const counterDetailsDiv = document.getElementById('counterDetails');
const counterNameEl = document.getElementById('counterName');
const counterIdSpan = document.getElementById('counterId');
const officeNameSpan = document.getElementById('officeName');
const statusBadge = document.getElementById('statusBadge');
const statusToggle = document.getElementById('statusToggle');
const statusTextSpan = document.getElementById('statusText');
const refreshBtn = document.getElementById('refreshTokensBtn');
const completeBtn = document.getElementById('completeCounterBtn');
const deleteCounterBtn = document.getElementById('deleteCounterBtn'); // Added
const tokensContainer = document.getElementById('tokensContainer');
const tokenCountSpan = document.getElementById('tokenCount');
const counterCountSpan = document.getElementById('counterCount');

// Modal elements
const arrivalModal = document.getElementById('arrivalModal');
const arrivalTimeInput = document.getElementById('arrivalTimeInput');
const saveArrivalBtn = document.getElementById('saveArrivalBtn');
const cancelArrivalBtn = document.getElementById('cancelArrivalBtn');
const closeModalBtn = document.getElementById('closeModalBtn');

// Confirmation Modal elements
const confirmModal = document.getElementById('confirmModal');
const confirmModalTitle = document.getElementById('confirmModalTitle');
const confirmMessage = document.getElementById('confirmMessage');
const confirmIcon = document.getElementById('confirmIcon');
const tokenInfoPreview = document.getElementById('tokenInfoPreview');
const previewTokenNumber = document.getElementById('previewTokenNumber');
const previewTokenDetails = document.getElementById('previewTokenDetails');
const confirmActionBtn = document.getElementById('confirmActionBtn');
const cancelConfirmBtn = document.getElementById('cancelConfirmBtn');
const closeConfirmModalBtn = document.getElementById('closeConfirmModalBtn');

// Helper: escape HTML
function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

// Show custom confirmation modal
function showConfirmModal(options) {
    return new Promise((resolve) => {
        // Set modal type (danger, success, info, warning)
        const type = options.type || 'default';
        confirmModal.className = `modal confirm-modal ${type}`;
        
        // Set title
        if (options.title) {
            confirmModalTitle.innerHTML = options.title;
        } else {
            confirmModalTitle.innerHTML = '<i class="fas fa-question-circle"></i> Confirm Action';
        }
        
        // Set icon based on type
        let iconHtml = '';
        switch(type) {
            case 'danger':
                iconHtml = '<i class="fas fa-exclamation-triangle"></i>';
                break;
            case 'success':
                iconHtml = '<i class="fas fa-check-circle"></i>';
                break;
            case 'info':
                iconHtml = '<i class="fas fa-info-circle"></i>';
                break;
            case 'warning':
                iconHtml = '<i class="fas fa-clock"></i>';
                break;
            default:
                iconHtml = '<i class="fas fa-question-circle"></i>';
        }
        confirmIcon.innerHTML = iconHtml;
        
        // Set message
        confirmMessage.textContent = options.message || 'Are you sure you want to perform this action?';
        
        // Show/hide token preview
        if (options.token) {
            tokenInfoPreview.style.display = 'block';
            previewTokenNumber.textContent = options.token.tokenNumber || 'N/A';
            
            let detailsHtml = '';
            if (options.token.serviceName) {
                detailsHtml += `<div><span class="label">Service:</span> <span>${escapeHtml(options.token.serviceName)}</span></div>`;
            }
            if (options.token.queueName) {
                detailsHtml += `<div><span class="label">Queue:</span> <span>${escapeHtml(options.token.queueName)}</span></div>`;
            }
            if (options.token.queueType) {
                detailsHtml += `<div><span class="label">Queue Type:</span> <span>${escapeHtml(options.token.queueType)}</span></div>`;
            }
            if (options.token.position) {
                detailsHtml += `<div><span class="label">Position:</span> <span>${options.token.position}</span></div>`;
            }
            previewTokenDetails.innerHTML = detailsHtml;
        } else {
            tokenInfoPreview.style.display = 'none';
        }
        
        // Set button text
        if (options.confirmText) {
            confirmActionBtn.textContent = options.confirmText;
        } else {
            confirmActionBtn.textContent = 'Confirm';
        }
        
        if (options.cancelText) {
            cancelConfirmBtn.textContent = options.cancelText;
        } else {
            cancelConfirmBtn.textContent = 'Cancel';
        }
        
        // Store resolve function
        pendingAction = resolve;
        pendingActionData = options.actionData;
        
        // Show modal
        confirmModal.style.display = 'flex';
    });
}

// Close confirmation modal
function closeConfirmModal() {
    confirmModal.style.display = 'none';
    if (pendingAction) {
        pendingAction(false);
        pendingAction = null;
    }
}

// Load all counters for this office
async function loadCounters() {
    try {
        const res = await fetch('/admin/api/counters');
        if (!res.ok) throw new Error('Failed to load counters');
        const counters = await res.json();
        
        if (!counters.length) {
            countersListEl.innerHTML = '<div class="empty-state">No counters found for your office</div>';
            counterCountSpan.textContent = '0';
            return;
        }
        
        counterCountSpan.textContent = counters.length;
        countersListEl.innerHTML = counters.map(counter => `
            <div class="counter-item" data-id="${counter.id}" onclick="selectCounter('${counter.id}')">
                <div class="counter-name">${escapeHtml(counter.name)}</div>
                <div class="counter-id">ID: ${counter.id}</div>
                <div class="counter-status ${counter.status === 'active' ? 'status-active' : 'status-inactive'}">
                    ${counter.status.toUpperCase()}
                </div>
            </div>
        `).join('');
    } catch (err) {
        console.error(err);
        countersListEl.innerHTML = '<div class="empty-state">Error loading counters</div>';
    }
}

// Select a counter
window.selectCounter = async function(counterId) {
    currentCounterId = counterId;
    
    // Highlight selected
    document.querySelectorAll('.counter-item').forEach(item => {
        item.classList.remove('selected');
        if (item.getAttribute('data-id') === counterId) {
            item.classList.add('selected');
        }
    });
    
    // Load details and tokens
    await loadCounterDetails(counterId);
    await loadTokens(counterId);
    
    noCounterDiv.style.display = 'none';
    counterDetailsDiv.style.display = 'block';
};

// Load counter details
async function loadCounterDetails(counterId) {
    try {
        const res = await fetch(`/admin/api/counter/${counterId}`);
        if (!res.ok) throw new Error('Counter not found');
        const data = await res.json();
        
        counterNameEl.textContent = data.name;
        counterIdSpan.textContent = `ID: ${data.id}`;
        officeNameSpan.textContent = data.officeName || 'No Office';
        
        const isActive = data.status === 'active';
        statusToggle.checked = isActive;
        statusTextSpan.textContent = isActive ? 'Active' : 'Inactive';
        statusBadge.textContent = isActive ? 'ACTIVE' : 'INACTIVE';
        statusBadge.className = `status-pill ${isActive ? 'active' : 'inactive'}`;
    } catch (err) {
        console.error(err);
        showToast('Error loading counter details', 'error');
    }
}

// Show toast notification (simple alert replacement)
function showToast(message, type = 'info') {
    // Create toast element if not exists
    let toast = document.getElementById('customToast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'customToast';
        toast.style.cssText = `
            position: fixed;
            bottom: 30px;
            right: 30px;
            padding: 14px 24px;
            border-radius: 12px;
            font-weight: 500;
            z-index: 10000;
            animation: slideInRight 0.3s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            max-width: 350px;
        `;
        document.body.appendChild(toast);
        
        // Add animation styles if not present
        if (!document.querySelector('#toastStyles')) {
            const style = document.createElement('style');
            style.id = 'toastStyles';
            style.textContent = `
                @keyframes slideInRight {
                    from {
                        opacity: 0;
                        transform: translateX(100px);
                    }
                    to {
                        opacity: 1;
                        transform: translateX(0);
                    }
                }
                @keyframes slideOutRight {
                    from {
                        opacity: 1;
                        transform: translateX(0);
                    }
                    to {
                        opacity: 0;
                        transform: translateX(100px);
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    // Set color based on type
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#3b82f6'
    };
    
    toast.style.backgroundColor = colors[type] || colors.info;
    toast.style.color = 'white';
    toast.textContent = message;
    toast.style.display = 'block';
    
    // Hide after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => {
            toast.style.display = 'none';
            toast.style.animation = '';
        }, 300);
    }, 3000);
}

// Show Lottie loader in tokens container
function showTokenLoader() {
    tokensContainer.innerHTML = `
        <div class="loading-state">
            <dotlottie-wc src="https://lottie.host/3d6adda6-880d-4ffc-94b2-50db5e89f1e0/eWLnP5z6OG.lottie" style="width: 100px; height: 100px;" autoplay loop></dotlottie-wc>
            <p>Loading tokens...</p>
        </div>
    `;
}

// Load tokens for selected counter
async function loadTokens(counterId) {
    showTokenLoader();
    
    try {
        const res = await fetch(`/admin/api/counter/${counterId}/tokens`);
        const tokens = await res.json();
        
        if (!tokens.length) {
            tokensContainer.innerHTML = '<div class="empty-state"><i class="fas fa-inbox"></i><p>No active tokens for this counter today.</p></div>';
            tokenCountSpan.textContent = '0';
            return;
        }
        
        tokenCountSpan.textContent = tokens.length;
        
        let html = '';
        tokens.forEach(token => {
            let statusClass = token.status;
            html += `
                <div class="token-card ${statusClass}" data-token-id="${token.id}" data-token-number="${escapeHtml(token.tokenNumber)}" data-service="${escapeHtml(token.serviceName)}" data-queue="${escapeHtml(token.queueName)}" data-queue-type="${escapeHtml(token.queueType)}" data-position="${token.position}">
                    <div class="token-number">${escapeHtml(token.tokenNumber)}</div>
                    <div class="token-details">
                        <div class="detail-row"><span class="detail-label">Service:</span> ${escapeHtml(token.serviceName)}</div>
                        <div class="detail-row"><span class="detail-label">Queue:</span> ${escapeHtml(token.queueName)}</div>
                        <div class="detail-row"><span class="detail-label">Queue Type:</span> ${escapeHtml(token.queueType)}</div>
                        <div class="detail-row"><span class="detail-label">Status:</span> <strong>${token.status.toUpperCase()}</strong></div>
                        <div class="detail-row"><span class="detail-label">Position:</span> ${token.position}</div>
                    </div>
                    <div class="token-actions">
                        <button class="token-btn serve-btn" onclick="actionToken('serve', '${token.id}')">
                            <i class="fas fa-check"></i> Serve
                        </button>
                        <button class="token-btn skip-btn" onclick="actionToken('skip', '${token.id}')">
                            <i class="fas fa-times"></i> Skip
                        </button>
                        <button class="token-btn arrival-btn" onclick="openArrivalModal('${token.id}')">
                            <i class="fas fa-clock"></i> Set Arrival
                        </button>
                    </div>
                </div>
            `;
        });
        tokensContainer.innerHTML = html;
    } catch (err) {
        console.error(err);
        tokensContainer.innerHTML = '<div class="empty-state" style="color:#dc2626;">Error loading tokens</div>';
    }
}

// Get token data from DOM
function getTokenDataFromCard(tokenId) {
    const card = document.querySelector(`.token-card[data-token-id="${tokenId}"]`);
    if (card) {
        return {
            tokenNumber: card.getAttribute('data-token-number'),
            serviceName: card.getAttribute('data-service'),
            queueName: card.getAttribute('data-queue'),
            queueType: card.getAttribute('data-queue-type'),
            position: card.getAttribute('data-position')
        };
    }
    return null;
}

// Token actions with custom modal
window.actionToken = async function(action, tokenId) {
    let title = '';
    let message = '';
    let type = 'default';
    let confirmText = '';
    
    const tokenData = getTokenDataFromCard(tokenId);
    
    switch(action) {
        case 'serve':
            title = '<i class="fas fa-check-circle"></i> Serve Token';
            message = `Are you sure you want to serve this token?`;
            type = 'success';
            confirmText = 'Yes, Serve';
            break;
        case 'skip':
            title = '<i class="fas fa-times-circle"></i> Skip Token';
            message = `Are you sure you want to skip this token? This action cannot be undone.`;
            type = 'danger';
            confirmText = 'Yes, Skip';
            break;
        default:
            title = '<i class="fas fa-question-circle"></i> Confirm Action';
            message = `Are you sure you want to ${action} this token?`;
            type = 'default';
            confirmText = 'Confirm';
    }
    
    const confirmed = await showConfirmModal({
        title: title,
        message: message,
        type: type,
        confirmText: confirmText,
        token: tokenData,
        actionData: { action, tokenId }
    });
    
    if (confirmed) {
        try {
            const res = await fetch(`/admin/api/token/${tokenId}/${action}`, { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                showToast(`Token ${action === 'serve' ? 'served' : 'skipped'} successfully!`, 'success');
                if (currentCounterId) loadTokens(currentCounterId);
            } else {
                showToast('Error: ' + (data.error || 'Unknown error'), 'error');
            }
        } catch (err) {
            showToast('Network error: ' + err.message, 'error');
        }
    }
};

// Update counter status
async function updateCounterStatus(counterId, isActive) {
    const newStatus = isActive ? 'active' : 'inactive';
    try {
        const res = await fetch(`/admin/api/counter/${counterId}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        const data = await res.json();
        if (data.success) {
            statusTextSpan.textContent = isActive ? 'Active' : 'Inactive';
            statusBadge.textContent = isActive ? 'ACTIVE' : 'INACTIVE';
            statusBadge.className = `status-pill ${isActive ? 'active' : 'inactive'}`;
            showToast(`Counter ${isActive ? 'activated' : 'deactivated'} successfully!`, 'success');
            // Refresh counters list to update status there as well
            loadCounters();
        } else {
            showToast('Failed to update status', 'error');
            statusToggle.checked = !isActive;
        }
    } catch (err) {
        showToast('Error updating status', 'error');
        statusToggle.checked = !isActive;
    }
}

// Complete counter (clear today's tokens) with custom modal
async function completeCounter(counterId) {
    const confirmed = await showConfirmModal({
        title: '<i class="fas fa-exclamation-triangle"></i> Complete Counter',
        message: '⚠️ WARNING: This will DELETE ALL ACTIVE TOKENS for this counter for TODAY. This action cannot be undone!',
        type: 'warning',
        confirmText: 'Yes, Complete Counter',
        cancelText: 'Cancel'
    });
    
    if (confirmed) {
        try {
            const res = await fetch(`/admin/api/counter/${counterId}/complete`, { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                showToast(`Successfully cleared ${data.deletedCount || 0} tokens.`, 'success');
                loadTokens(counterId);
            } else {
                showToast('Error: ' + (data.error || 'Unknown'), 'error');
            }
        } catch (err) {
            showToast('Network error: ' + err.message, 'error');
        }
    }
}

// Delete counter (permanently remove counter and ALL tokens)
async function deleteCounter(counterId) {
    // First get counter name for better confirmation message
    let counterName = 'this counter';
    try {
        const res = await fetch(`/admin/api/counter/${counterId}`);
        if (res.ok) {
            const data = await res.json();
            counterName = data.name;
        }
    } catch (err) {
        console.error('Error fetching counter name:', err);
    }
    
    const confirmed = await showConfirmModal({
        title: '<i class="fas fa-exclamation-triangle"></i> DELETE COUNTER PERMANENTLY',
        message: `⚠️ IMPORTANT ⚠️\n\nYou are about to PERMANENTLY DELETE counter "${counterName}" and ALL its associated tokens (past and present).\n\nwill also be deleted with tokens\n\nAre you absolutely sure?`,
        type: 'danger',
        confirmText: 'Yes, Delete Permanently',
        cancelText: 'Cancel'
    });
    
    if (confirmed) {
        // Show loading state
        showToast('Deleting counter and all associated tokens...', 'warning');
        
        try {
            const res = await fetch(`/admin/api/counter/${counterId}/delete`, { 
                method: 'DELETE' 
            });
            const data = await res.json();
            
            if (data.success) {
                showToast(`✅ Counter "${data.counterName || counterName}" deleted successfully! ${data.deletedTokensCount || 0} tokens were also removed.`, 'success');
                
                // Clear current selection
                currentCounterId = null;
                counterDetailsDiv.style.display = 'none';
                noCounterDiv.style.display = 'block';
                
                // Refresh counters list
                await loadCounters();
                
                // Clear tokens display
                tokensContainer.innerHTML = '<div class="empty-state"><i class="fas fa-inbox"></i><p>Select a counter to view tokens</p></div>';
                tokenCountSpan.textContent = '0';
            } else {
                showToast('Error: ' + (data.error || 'Unknown error'), 'error');
            }
        } catch (err) {
            showToast('Network error: ' + err.message, 'error');
        }
    }
}

// Arrival modal
window.openArrivalModal = function(tokenId) {
    currentTokenIdForArrival = tokenId;
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    arrivalTimeInput.value = `${hours}:${minutes}`;
    arrivalModal.style.display = 'flex';
};

function closeArrivalModal() {
    arrivalModal.style.display = 'none';
    currentTokenIdForArrival = null;
}

async function saveArrival() {
    if (!currentTokenIdForArrival) return;
    const timeStr = arrivalTimeInput.value;
    if (!timeStr) return;
    
    const [hours, minutes] = timeStr.split(':');
    const now = new Date();
    const dt = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate(), parseInt(hours), parseInt(minutes), 0));
    const utcSeconds = dt.getTime() / 1000;
    
    try {
        const res = await fetch(`/admin/api/token/${currentTokenIdForArrival}/arrive`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ arrivedtime: utcSeconds })
        });
        const data = await res.json();
        if (data.success) {
            showToast('Arrival time set successfully!', 'success');
            closeArrivalModal();
            if (currentCounterId) loadTokens(currentCounterId);
        } else {
            showToast('Error: ' + (data.error || 'Unknown'), 'error');
        }
    } catch (err) {
        showToast('Network error: ' + err.message, 'error');
    }
}

// Event listeners
statusToggle.addEventListener('change', (e) => {
    if (currentCounterId) {
        updateCounterStatus(currentCounterId, e.target.checked);
    } else {
        e.target.checked = false;
    }
});

refreshBtn.addEventListener('click', () => {
    if (currentCounterId) {
        showToast('Refreshing tokens...', 'info');
        loadTokens(currentCounterId);
    }
});

completeBtn.addEventListener('click', () => {
    if (currentCounterId) completeCounter(currentCounterId);
});

// Delete counter event listener
if (deleteCounterBtn) {
    deleteCounterBtn.addEventListener('click', () => {
        if (currentCounterId) deleteCounter(currentCounterId);
    });
}

saveArrivalBtn.addEventListener('click', saveArrival);
cancelArrivalBtn.addEventListener('click', closeArrivalModal);
closeModalBtn.addEventListener('click', closeArrivalModal);

// Confirmation modal event listeners
confirmActionBtn.addEventListener('click', () => {
    confirmModal.style.display = 'none';
    if (pendingAction) {
        pendingAction(true);
        pendingAction = null;
    }
});

cancelConfirmBtn.addEventListener('click', closeConfirmModal);
closeConfirmModalBtn.addEventListener('click', closeConfirmModal);

// Close modals when clicking outside
window.addEventListener('click', (e) => {
    if (e.target === arrivalModal) closeArrivalModal();
    if (e.target === confirmModal) closeConfirmModal();
});

// Initial load
loadCounters();