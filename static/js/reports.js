// Helper to format timestamp for report generation time
function formatGenerationTime() {
    const now = new Date();
    return now.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
    });
}

// Helper to update generation timer
function updateGenerationTimer(elementId) {
    const timerElement = document.getElementById(elementId);
    if (timerElement) {
        timerElement.innerHTML = `📅 Last updated: ${formatGenerationTime()}`;
    }
}

// Load daily report
async function loadDaily() {
    try {
        // Show loading state (optional - you can remove this if you want no loading indicator)
        const table = document.getElementById('daily-table');
        if (table) table.style.opacity = '0.5';
        
        const resp = await fetch('/reports/api/daily');
        const data = await resp.json();
        
        if (!data.success) {
            console.error('Daily API error:', data);
            return;
        }

        // Render bar chart
        const chartDiv = document.getElementById('daily-chart');
        if (chartDiv && data.chart_html) {
            chartDiv.innerHTML = data.chart_html;
            const scripts = chartDiv.getElementsByTagName('script');
            for (let script of scripts) eval(script.textContent);
        }

        // Render pie chart
        const pieDiv = document.getElementById('daily-pie');
        if (pieDiv) {
            if (data.pie_chart && data.pie_chart !== '<p>No queue data available</p>') {
                pieDiv.innerHTML = data.pie_chart;
                const pieScripts = pieDiv.getElementsByTagName('script');
                for (let script of pieScripts) eval(script.textContent);
                if (typeof echarts !== 'undefined') {
                    window.dispatchEvent(new Event('resize'));
                }
            } else {
                pieDiv.innerHTML = '<div class="no-data-message">📊 No queue data available for today</div>';
            }
        }

        // Summary table - NOW SHOWING WORKING HOURS instead of Avg Wait Time
        if (table) {
            table.innerHTML = `
                <thead>
                    <tr>
                        <th>📋 Metric</th>
                        <th>📊 Value</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>🎫 Total Tokens Today</td>
                        <td><strong>${data.data.total_tokens || 0}</strong></td>
                    </tr>
                    <tr>
                        <td>✅ Served</td>
                        <td><strong>${data.data.served || 0}</strong></td>
                    </tr>
                    <tr>
                        <td>⏳ Waiting</td>
                        <td><strong>${data.data.waiting || 0}</strong></td>
                    </tr>
                    <tr>
                        <td>🖥️ Active Counters</td>
                        <td><strong>${data.data.active_counters || 0}</strong></td>
                    </tr>
                    <tr style="background-color: #e8f5e9;">
                        <td>🕒 Office Working Hours</td>
                        <td><strong style="color: #2e7d32;">${data.data.office_working_hours || 'Not set'}</strong></td>
                    </tr>
                    <tr style="background-color: #f1f8e9;">
                        <td>⏱️ Working Duration (per day)</td>
                        <td><strong style="color: #2e7d32;">${data.data.office_working_duration || '8 hours'}</strong></td>
                    </tr>
                </tbody>
            `;
            table.style.opacity = '1';
        }

        // Queue performance table
        const queueTable = document.getElementById('daily-queue-table');
        if (queueTable) {
            if (data.data.queue_data && data.data.queue_data.length > 0) {
                let queueHtml = `
                    <thead>
                        <tr>
                            <th>🏢 Service / Queue</th>
                            <th>✅ Served</th>
                            <th>⏳ Waiting</th>
                            <th>⏱️ Avg Wait Time</th>
                        </tr>
                    </thead>
                    <tbody>
                `;
                for (let q of data.data.queue_data) {
                    queueHtml += `
                        <tr>
                            <td><strong>${q.service_name || q.queue_name || 'Unknown'}</strong></td>
                            <td>${q.tokens_served || 0}</td>
                            <td>${q.tokens_waiting || 0}</td>
                            <td>${(q.avg_wait_time && q.avg_wait_time !== 'N/A') ? q.avg_wait_time : '—'}</td>
                        </tr>
                    `;
                }
                queueHtml += `</tbody>`;
                queueTable.innerHTML = queueHtml;
            } else {
                queueTable.innerHTML = '<tbody><tr><td colspan="4">✅ No queue activity today</td></tr></tbody>';
            }
        }

        // Update generation timer
        updateGenerationTimer('daily-timer');
        
    } catch (error) {
        console.error('Error loading daily report:', error);
        const table = document.getElementById('daily-table');
        if (table) {
            table.innerHTML = '<tbody><tr><td colspan="2">❌ Error loading report</td></tr></tbody>';
            table.style.opacity = '1';
        }
    }
}

// Load weekly report
async function loadWeekly() {
    try {
        const resp = await fetch('/reports/api/weekly');
        const data = await resp.json();
        if (!data.success) return;

        const chartDiv = document.getElementById('weekly-chart');
        if (chartDiv && data.chart_html) {
            chartDiv.innerHTML = data.chart_html;
            const scripts = chartDiv.getElementsByTagName('script');
            for (let script of scripts) eval(script.textContent);
        }

        // Build weekly table with Working Hours instead of Avg Wait
        const tbody = document.querySelector('#weekly-table tbody');
        if (tbody) {
            tbody.innerHTML = '';
            for (let i = 0; i < data.labels.length; i++) {
                const workingHours = (data.working_hours && data.working_hours[i]) ? data.working_hours[i] : '8 hours';
                tbody.insertAdjacentHTML('beforeend', `
                    <tr>
                        <td><strong>${data.labels[i]}</strong></td>
                        <td>${data.served[i] || 0}</td>
                        <td>${data.waiting[i] || 0}</td>
                        <td>${data.active_counters ? data.active_counters[i] : '0'}</td>
                        <td style="color: #2e7d32; font-weight: 500;">${workingHours}</td>
                    </tr>
                `);
            }
        }

        // Queue summary table
        const queueTbody = document.querySelector('#weekly-queue-table tbody');
        if (queueTbody) {
            if (data.queue_summary && data.queue_summary.length > 0) {
                queueTbody.innerHTML = '';
                for (let q of data.queue_summary) {
                    queueTbody.insertAdjacentHTML('beforeend', `
                        <tr>
                            <td><strong>${q.service_name || 'Unknown'}</strong></td>
                            <td>${q.served || 0}</td>
                            <td>${q.waiting || 0}</td>
                            <td>${(q.avg_wait_time && q.avg_wait_time !== 'N/A') ? q.avg_wait_time : '—'}</td>
                        </tr>
                    `);
                }
            } else {
                queueTbody.innerHTML = '<tr><td colspan="4">📭 No queue data for this week</td></tr>';
            }
        }

        // Update generation timer
        updateGenerationTimer('weekly-timer');
        
    } catch (error) {
        console.error('Error loading weekly report:', error);
    }
}

// Load monthly report
async function loadMonthly() {
    try {
        const resp = await fetch('/reports/api/monthly');
        const data = await resp.json();
        if (!data.success) return;

        const chartDiv = document.getElementById('monthly-chart');
        if (chartDiv && data.chart_html) {
            chartDiv.innerHTML = data.chart_html;
            const scripts = chartDiv.getElementsByTagName('script');
            for (let script of scripts) eval(script.textContent);
        }

        // Build monthly table with Working Hours instead of Avg Wait
        const tbody = document.querySelector('#monthly-table tbody');
        if (tbody) {
            tbody.innerHTML = '';
            for (let i = 0; i < data.labels.length; i++) {
                const workingHours = (data.working_hours && data.working_hours[i]) ? data.working_hours[i] : '8 hours';
                tbody.insertAdjacentHTML('beforeend', `
                    <tr>
                        <td><strong>${data.labels[i]}</strong></td>
                        <td>${data.served[i] || 0}</td>
                        <td>${data.waiting[i] || 0}</td>
                        <td>${data.active_counters ? data.active_counters[i] : '0'}</td>
                        <td style="color: #2e7d32; font-weight: 500;">${workingHours}</td>
                    </tr>
                `);
            }
        }

        // Queue summary table
        const queueTbody = document.querySelector('#monthly-queue-table tbody');
        if (queueTbody) {
            if (data.queue_summary && data.queue_summary.length > 0) {
                queueTbody.innerHTML = '';
                for (let q of data.queue_summary) {
                    queueTbody.insertAdjacentHTML('beforeend', `
                        <tr>
                            <td><strong>${q.service_name || 'Unknown'}</strong></td>
                            <td>${q.served || 0}</td>
                            <td>${q.waiting || 0}</td>
                            <td>${(q.avg_wait_time && q.avg_wait_time !== 'N/A') ? q.avg_wait_time : '—'}</td>
                        </tr>
                    `);
                }
            } else {
                queueTbody.innerHTML = '<tr><td colspan="4">📭 No queue data for this month</td></tr>';
            }
        }

        // Update generation timer
        updateGenerationTimer('monthly-timer');
        
    } catch (error) {
        console.error('Error loading monthly report:', error);
    }
}

// Get currently active tab ID
function getActiveTabId() {
    const activeTab = document.querySelector('.tab-btn.active');
    return activeTab ? activeTab.dataset.tab : 'daily';
}

// Refresh the currently active report
async function refreshReport() {
    const activeTab = getActiveTabId();
    if (activeTab === 'daily') await loadDaily();
    else if (activeTab === 'weekly') await loadWeekly();
    else if (activeTab === 'monthly') await loadMonthly();
}

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tabId = btn.dataset.tab;
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
        document.getElementById(tabId).classList.add('active');

        if (tabId === 'daily') loadDaily();
        else if (tabId === 'weekly') loadWeekly();
        else if (tabId === 'monthly') loadMonthly();
    });
});

// PDF download buttons
document.querySelectorAll('.download-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const type = btn.dataset.type;
        window.open(`/reports/download/${type}`, '_blank');
    });
});

// Add refresh button (without mouse loading effects)
function addRefreshButtons() {
    const headers = document.querySelectorAll('.report-header');
    headers.forEach(header => {
        if (header.querySelector('.refresh-btn')) return;
        
        // Add generation timer span if not exists
        let timerSpan = header.querySelector('.generation-timer');
        if (!timerSpan && header.parentElement) {
            timerSpan = document.createElement('span');
            timerSpan.className = 'generation-timer';
            timerSpan.id = `${header.parentElement.id || 'daily'}-timer`;
            timerSpan.style.marginLeft = 'auto';
            timerSpan.style.fontSize = '12px';
            timerSpan.style.color = '#666';
            timerSpan.style.padding = '8px 12px';
            header.appendChild(timerSpan);
        }
        
        const refreshBtn = document.createElement('button');
        refreshBtn.className = 'refresh-btn';
        refreshBtn.innerHTML = '🔄 Refresh';
        refreshBtn.style.marginLeft = '12px';
        refreshBtn.style.backgroundColor = '#2e7d32';
        refreshBtn.style.color = 'white';
        refreshBtn.style.border = 'none';
        refreshBtn.style.padding = '8px 16px';
        refreshBtn.style.borderRadius = '40px';
        refreshBtn.style.cursor = 'pointer';
        refreshBtn.style.fontWeight = '600';
        refreshBtn.style.transition = 'all 0.2s';
        refreshBtn.onmouseover = () => refreshBtn.style.backgroundColor = '#1b5e20';
        refreshBtn.onmouseout = () => refreshBtn.style.backgroundColor = '#2e7d32';
        refreshBtn.addEventListener('click', () => refreshReport());
        header.appendChild(refreshBtn);
    });
}

// Add timer containers to each report header
function addTimerContainers() {
    const reportContents = document.querySelectorAll('.report-content');
    reportContents.forEach(content => {
        const header = content.querySelector('.report-header');
        if (header && !header.querySelector('.generation-timer')) {
            const timerSpan = document.createElement('span');
            timerSpan.className = 'generation-timer';
            timerSpan.id = `${content.id || 'daily'}-timer`;
            timerSpan.style.marginLeft = 'auto';
            timerSpan.style.fontSize = '12px';
            timerSpan.style.color = '#666';
            timerSpan.style.padding = '8px 12px';
            header.appendChild(timerSpan);
        }
    });
}

// Initialize everything
document.addEventListener('DOMContentLoaded', () => {
    addTimerContainers();
    addRefreshButtons();
    loadDaily(); // Load daily by default
});