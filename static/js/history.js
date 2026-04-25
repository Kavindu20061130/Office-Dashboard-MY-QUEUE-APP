let currentTokenId = null;
let currentBookedTime = null;

// Load tokens with current filters
async function loadTokens() {
    const queueId = document.getElementById('filterQueue').value;
    const serviceId = document.getElementById('filterService').value;
    const counterId = document.getElementById('filterCounter').value;
    const dateFrom = document.getElementById('filterDateFrom').value;
    const dateTo = document.getElementById('filterDateTo').value;
    const searchType = document.getElementById('searchType').value;
    const searchValue = document.getElementById('searchValue').value;

    const params = new URLSearchParams();
    if (queueId) params.append('queueId', queueId);
    if (serviceId) params.append('serviceId', serviceId);
    if (counterId) params.append('counterId', counterId);
    if (dateFrom) params.append('dateFrom', dateFrom);
    if (dateTo) params.append('dateTo', dateTo);
    if (searchType && searchValue) {
        params.append('searchType', searchType);
        params.append('searchValue', searchValue);
    }

    try {
        const response = await fetch(`/admin/api/history/tokens?${params.toString()}`);
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        renderTable(data.tokens || []);
    } catch (err) {
        console.error(err);
        document.getElementById('historyTableBody').innerHTML = `
            <tr><td colspan="9" class="loading-state" style="color:#dc2626;">Error loading tokens: ${err.message}</td></tr>
        `;
    }
}

function renderTable(tokens) {
    const tbody = document.getElementById('historyTableBody');
    if (tokens.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="loading-state">No tokens found</td></tr>';
        return;
    }

    let html = '';
    tokens.forEach(token => {
        const bookedTime = token.bookedTime ? new Date(token.bookedTime * 1000).toLocaleString() : '—';
        let statusClass = '';
        if (token.status === 'served') statusClass = 'status-served';
        else if (token.status === 'cancelled') statusClass = 'status-cancelled';
        else if (token.status === 'skipped') statusClass = 'status-skipped';

        // Pass token.bookedTime to the modal opener
        html += `
            <tr data-token-id="${token.id}">
                <td><strong>${escapeHtml(token.tokenNumber)}</strong></td>
                <td style="font-family: monospace; font-size: 0.75rem;">${escapeHtml(token.id)}</td>
                <td><span class="status-badge ${statusClass}">${token.status.toUpperCase()}</span></td>
                <td>${escapeHtml(token.serviceName || '—')}</td>
                <td>${escapeHtml(token.queueName || '—')}</td>
                <td>${escapeHtml(token.counterName || '—')}</td>
                <td>${token.position || '—'}</td>
                <td>${bookedTime}</td>
                <td>
                    <button class="action-btn" onclick="openStatusModal('${token.id}', '${escapeHtml(token.tokenNumber)}', '${token.status}', ${token.bookedTime || 'null'})">
                        <i class="fa-solid fa-pen-to-square"></i> Change Status
                    </button>
                </td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, m => {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

// Open modal for status change (with optional booked time editor)
function openStatusModal(tokenId, tokenNumber, currentStatus, bookedTimestamp) {
    currentTokenId = tokenId;
    currentBookedTime = bookedTimestamp;
    
    const modal = document.getElementById('statusModal');
    const message = document.getElementById('statusModalMessage');
    const preview = document.getElementById('tokenPreview');
    const datetimeInput = document.getElementById('newBookedTime');
    
    // Set datetime input to current booked time (if exists)
    if (bookedTimestamp) {
        const bookedDate = new Date(bookedTimestamp * 1000);
        const year = bookedDate.getFullYear();
        const month = String(bookedDate.getMonth() + 1).padStart(2, '0');
        const day = String(bookedDate.getDate()).padStart(2, '0');
        const hours = String(bookedDate.getHours()).padStart(2, '0');
        const minutes = String(bookedDate.getMinutes()).padStart(2, '0');
        datetimeInput.value = `${year}-${month}-${day}T${hours}:${minutes}`;
    } else {
        datetimeInput.value = '';
    }
    
    let actionText = '';
    if (currentStatus === 'served') {
        actionText = 'waiting (this will remove arrival and served times)';
    } else if (currentStatus === 'cancelled') {
        actionText = 'waiting (token will become active again)';
    } else if (currentStatus === 'skipped') {
        actionText = 'waiting (token will become active again)';
    }
    
    message.innerHTML = `
        Are you sure you want to change token <strong>${escapeHtml(tokenNumber)}</strong> 
        from <strong>${currentStatus.toUpperCase()}</strong> to <strong>WAITING</strong>?<br><br>
        ${actionText}.<br><br>
        You may also change the booked date/time below (optional).
    `;
    
    preview.innerHTML = `
        <div><strong>Token Number:</strong> ${escapeHtml(tokenNumber)}</div>
        <div><strong>Current Status:</strong> ${currentStatus.toUpperCase()}</div>
        <div><strong>New Status:</strong> WAITING</div>
    `;
    modal.style.display = 'flex';
}

async function confirmStatusChange() {
    const modal = document.getElementById('statusModal');
    const datetimeInput = document.getElementById('newBookedTime');
    let newBookedTimestamp = null;
    
    if (datetimeInput.value) {
        const bookedDate = new Date(datetimeInput.value);
        if (!isNaN(bookedDate.getTime())) {
            newBookedTimestamp = Math.floor(bookedDate.getTime() / 1000);
        }
    }
    
    try {
        const response = await fetch('/admin/api/history/change-status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tokenId: currentTokenId,
                newStatus: 'waiting',
                bookedTime: newBookedTimestamp
            })
        });
        const data = await response.json();
        if (data.success) {
            showToast(data.message || 'Status changed successfully', 'success');
            closeStatusModal();
            loadTokens(); // refresh table
        } else {
            showToast(data.error || 'Failed to change status', 'error');
        }
    } catch (err) {
        showToast('Network error: ' + err.message, 'error');
    }
}

function closeStatusModal() {
    document.getElementById('statusModal').style.display = 'none';
    currentTokenId = null;
    currentBookedTime = null;
}

function showToast(message, type = 'info') {
    let toast = document.getElementById('customToast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'customToast';
        toast.style.cssText = `
            position: fixed;
            bottom: 30px;
            right: 30px;
            padding: 12px 20px;
            border-radius: 12px;
            font-weight: 500;
            z-index: 10000;
            animation: slideInRight 0.3s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            max-width: 350px;
        `;
        document.body.appendChild(toast);
        if (!document.querySelector('#toastStyles')) {
            const style = document.createElement('style');
            style.textContent = `
                @keyframes slideInRight {
                    from { opacity: 0; transform: translateX(100px); }
                    to { opacity: 1; transform: translateX(0); }
                }
                @keyframes slideOutRight {
                    from { opacity: 1; transform: translateX(0); }
                    to { opacity: 0; transform: translateX(100px); }
                }
            `;
            document.head.appendChild(style);
        }
    }
    const colors = { success: '#10b981', error: '#ef4444', warning: '#f59e0b', info: '#3b82f6' };
    toast.style.backgroundColor = colors[type] || colors.info;
    toast.style.color = 'white';
    toast.textContent = message;
    toast.style.display = 'block';
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => {
            toast.style.display = 'none';
            toast.style.animation = '';
        }, 300);
    }, 3000);
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    const filters = ['filterQueue', 'filterService', 'filterCounter', 'filterDateFrom', 'filterDateTo'];
    filters.forEach(id => {
        document.getElementById(id).addEventListener('change', () => loadTokens());
    });
    document.getElementById('searchBtn').addEventListener('click', () => loadTokens());
    document.getElementById('clearFiltersBtn').addEventListener('click', () => {
        document.getElementById('filterQueue').value = '';
        document.getElementById('filterService').value = '';
        document.getElementById('filterCounter').value = '';
        document.getElementById('filterDateFrom').value = '';
        document.getElementById('filterDateTo').value = '';
        document.getElementById('searchType').value = 'tokenNumber';
        document.getElementById('searchValue').value = '';
        loadTokens();
    });
    
    const modal = document.getElementById('statusModal');
    modal.querySelector('.close-modal').addEventListener('click', closeStatusModal);
    modal.querySelector('.cancel-btn').addEventListener('click', closeStatusModal);
    modal.querySelector('.confirm-btn').addEventListener('click', confirmStatusChange);
    window.addEventListener('click', (e) => {
        if (e.target === modal) closeStatusModal();
    });
    
    loadTokens();
});