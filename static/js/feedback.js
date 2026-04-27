let currentPage = 1;
let feedbacksData = [];
let currentSort = { field: 'created_at', order: 'desc' };
let ratingChart = null, ratingBarChart = null, trendLineChart = null;

const container = document.querySelector('.feedback-container');
const officeId = container.dataset.officeId;

document.addEventListener('DOMContentLoaded', () => {
    loadDropdowns();
    document.getElementById('applyFiltersBtn').addEventListener('click', () => {
        currentPage = 1;
        loadFeedbackData();
    });
    document.getElementById('clearFiltersBtn').addEventListener('click', clearFilters);
    
    document.querySelectorAll('#feedbackTable th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const field = th.dataset.sort;
            if (currentSort.field === field) {
                currentSort.order = currentSort.order === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.field = field;
                currentSort.order = 'desc';
            }
            loadFeedbackData();
        });
    });
    
    loadFeedbackData();
});

function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = show ? 'flex' : 'none';
}

function closeLoadingOverlay() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

async function loadDropdowns() {
    try {
        const [queuesRes, countersRes, servicesRes] = await Promise.all([
            fetch('/feedback/api/queues'),
            fetch('/feedback/api/counters'),
            fetch('/feedback/api/services')
        ]);
        const queues = await queuesRes.json();
        const counters = await countersRes.json();
        const services = await servicesRes.json();

        const queueSelect = document.getElementById('queueFilter');
        queueSelect.innerHTML = '<option value="">All Queues</option>';
        (queues.queues || []).forEach(q => queueSelect.appendChild(new Option(q.name, q.id)));

        const counterSelect = document.getElementById('counterFilter');
        counterSelect.innerHTML = '<option value="">All Counters</option>';
        (counters.counters || []).forEach(c => counterSelect.appendChild(new Option(c.name, c.id)));

        const serviceSelect = document.getElementById('serviceFilter');
        serviceSelect.innerHTML = '<option value="">All Services</option>';
        (services.services || []).forEach(s => serviceSelect.appendChild(new Option(s.name, s.id)));
    } catch (err) {
        console.error('Dropdown load error:', err);
    }
}

async function loadFeedbackData() {
    showLoading(true);
    const params = new URLSearchParams({
        queue_id: document.getElementById('queueFilter').value,
        counter_id: document.getElementById('counterFilter').value,
        service_id: document.getElementById('serviceFilter').value,
        from_date: document.getElementById('fromDateFilter').value,
        to_date: document.getElementById('toDateFilter').value,
        keyword: document.getElementById('keywordFilter').value,
        page: currentPage,
        sort_by: currentSort.field,
        sort_order: currentSort.order
    });

    try {
        const res = await fetch(`/feedback/api/data?${params}`);
        const data = await res.json();
        if (data.success) {
            feedbacksData = data.feedbacks;
            updateAnalytics(data.analytics);
            updateTable(data.feedbacks);
            updatePagination(data);
            updateTrendChart(data.line_chart);
        } else {
            document.getElementById('feedbacksTableBody').innerHTML = '<tr><td colspan="8" class="loading-td">Failed to load data</td></tr>';
        }
    } catch (err) {
        document.getElementById('feedbacksTableBody').innerHTML = '<tr><td colspan="8" class="loading-td">Network error</td></tr>';
    } finally {
        showLoading(false);
    }
}

function updateAnalytics(analytics) {
    document.getElementById('totalFeedbacks').textContent = analytics.total_feedbacks;
    document.getElementById('avgRating').textContent = analytics.average_rating + ' / 5';
    document.getElementById('mostCommonRating').textContent = analytics.most_common_rating || 'N/A';
    const dist = analytics.rating_distribution;
    const labels = ['Very Poor', 'Poor', 'Average', 'Good', 'Excellent'];
    const data = [
        dist['Very Poor'] || 0,
        dist['Poor'] || 0,
        dist['Average'] || 0,
        dist['Good'] || 0,
        dist['Excellent'] || 0
    ];
    const colors = ['#8b0000', '#d9534f', '#f0ad4e', '#5bc0de', '#147a33'];

    if (ratingChart) ratingChart.destroy();
    const pieCtx = document.getElementById('ratingChart').getContext('2d');
    ratingChart = new Chart(pieCtx, {
        type: 'pie',
        data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 0 }] },
        options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'bottom' } } }
    });

    if (ratingBarChart) ratingBarChart.destroy();
    const barCtx = document.getElementById('ratingBarChart').getContext('2d');
    ratingBarChart = new Chart(barCtx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Number of Feedbacks',
                data,
                backgroundColor: colors,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            scales: { y: { beginAtZero: true, title: { display: true, text: 'Count' } } },
            plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx) => `${ctx.raw} feedbacks` } } }
        }
    });
}

function updateTrendChart(lineData) {
    if (!lineData) return;
    if (trendLineChart) trendLineChart.destroy();
    const ctx = document.getElementById('trendLineChart').getContext('2d');
    trendLineChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: lineData.labels,
            datasets: [{
                label: 'Average Rating',
                data: lineData.data,
                borderColor: '#147a33',
                backgroundColor: 'rgba(20, 122, 51, 0.1)',
                tension: 0.3,
                fill: true,
                pointBackgroundColor: '#147a33',
                pointBorderColor: '#fff',
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: { y: { beginAtZero: true, max: 5, title: { display: true, text: 'Rating (1–5)' } } },
            plugins: { tooltip: { callbacks: { label: (ctx) => `Rating: ${ctx.raw} / 5` } } }
        }
    });
}

function updateTable(feedbacks) {
    const tbody = document.getElementById('feedbacksTableBody');
    if (!feedbacks.length) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading-td">No feedbacks found for your office.</td></tr>';
        return;
    }
    tbody.innerHTML = feedbacks.map(fb => {
        let ratingClass = '';
        if (fb.rating === 'Excellent') ratingClass = 'rating-excellent';
        else if (fb.rating === 'Good') ratingClass = 'rating-good';
        else if (fb.rating === 'Average') ratingClass = 'rating-average';
        else if (fb.rating === 'Poor') ratingClass = 'rating-poor';
        else if (fb.rating === 'Very Poor') ratingClass = 'rating-very-poor';
        return `
            <tr>
                <td><strong>${escapeHtml(fb.user_name)}</strong></td>
                <td><span class="rating-badge ${ratingClass}">${fb.rating}</span></td>
                <td class="comment-preview" title="${escapeHtml(fb.comment)}">${escapeHtml(fb.comment_preview)}</td>
                <td>${escapeHtml(fb.service.name)}</td>
                <td>${escapeHtml(fb.queue.name)}</td>
                <td>${escapeHtml(fb.counter.name)}</td>
                <td><small>${fb.created_at_formatted}</small></td>
                <td><button class="btn-view" onclick="showDetails('${fb.id}')"><i class="fa-solid fa-eye"></i> View</button></td>
            </tr>`;
    }).join('');
}

function updatePagination(data) {
    const div = document.getElementById('pagination');
    if (data.total_pages <= 1) { div.innerHTML = ''; return; }
    let html = '';
    for (let i = 1; i <= data.total_pages; i++) {
        html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
    }
    div.innerHTML = html;
}

function goToPage(page) { currentPage = page; loadFeedbackData(); }

function showDetails(feedbackId) {
    const fb = feedbacksData.find(f => f.id === feedbackId);
    if (!fb) return;
    const modalBody = document.getElementById('modalBody');
    modalBody.innerHTML = `
        <div class="detail-row"><div class="detail-label">User:</div><div class="detail-value">${escapeHtml(fb.user_name)}</div></div>
        <div class="detail-row"><div class="detail-label">Rating:</div><div class="detail-value"><span class="rating-badge rating-${fb.rating.toLowerCase().replace(' ', '-')}">${fb.rating}</span></div></div>
        <div class="detail-row"><div class="detail-label">Comment:</div><div class="detail-value">${escapeHtml(fb.comment)}</div></div>
        <div class="detail-row"><div class="detail-label">Service:</div><div class="detail-value">${escapeHtml(fb.service.name)} (ID: ${fb.service.id})</div></div>
        <div class="detail-row"><div class="detail-label">Queue:</div><div class="detail-value">${escapeHtml(fb.queue.name)} (ID: ${fb.queue.id})</div></div>
        <div class="detail-row"><div class="detail-label">Counter:</div><div class="detail-value">${escapeHtml(fb.counter.name)} (ID: ${fb.counter.id})</div></div>
        <div class="detail-row"><div class="detail-label">Office:</div><div class="detail-value">${escapeHtml(fb.office.name)}</div></div>
        <div class="detail-row"><div class="detail-label">Created:</div><div class="detail-value">${fb.created_at_formatted}</div></div>
        <div class="detail-row"><div class="detail-label">User ID:</div><div class="detail-value">${fb.user_id || 'N/A'}</div></div>`;
    document.getElementById('feedbackModal').style.display = 'flex';
}

function closeModal() { document.getElementById('feedbackModal').style.display = 'none'; }

function clearFilters() {
    document.getElementById('queueFilter').value = '';
    document.getElementById('counterFilter').value = '';
    document.getElementById('serviceFilter').value = '';
    document.getElementById('fromDateFilter').value = '';
    document.getElementById('toDateFilter').value = '';
    document.getElementById('keywordFilter').value = '';
    currentPage = 1;
    loadFeedbackData();
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[m]));
}

window.onclick = event => {
    const modal = document.getElementById('feedbackModal');
    if (event.target === modal) closeModal();
};