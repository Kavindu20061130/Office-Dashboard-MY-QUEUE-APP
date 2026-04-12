let currentTokenId = null;
let currentServingId = null;
let updateInterval = null;
let isUpdating = false;
let lastUpdateTimestamp = 0;
let servingStartTime = null;

// ===== SCROLL BUTTON STATE =====
let isAtBottom = false;
const scrollFab = document.getElementById('scrollFab');
const scrollIcon = document.getElementById('scrollIcon');
const mainContainer = document.querySelector('.main');

function updateScrollButtonState() {
    if (!mainContainer) return;
    const scrollTop = mainContainer.scrollTop;
    const scrollHeight = mainContainer.scrollHeight;
    const clientHeight = mainContainer.clientHeight;
    const atBottom = Math.ceil(scrollTop + clientHeight) >= scrollHeight - 10;
    
    if (atBottom !== isAtBottom) {
        isAtBottom = atBottom;
        if (isAtBottom) {
            scrollIcon.className = 'fa-solid fa-chevron-up';
            document.querySelector('.scroll-tooltip').textContent = 'Scroll to top';
        } else {
            scrollIcon.className = 'fa-solid fa-chevron-down';
            document.querySelector('.scroll-tooltip').textContent = 'Scroll to bottom';
        }
    }
}

function toggleScroll() {
    if (!mainContainer) return;
    if (isAtBottom) {
        mainContainer.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
        mainContainer.scrollTo({ top: mainContainer.scrollHeight, behavior: 'smooth' });
    }
}

// Listen to scroll events
if (mainContainer) {
    mainContainer.addEventListener('scroll', updateScrollButtonState);
    // Initial check after content loads
    setTimeout(updateScrollButtonState, 500);
}

// ===== TIME HELPERS =====
function formatTimeShort(ts) {
    if (!ts) return "—";
    const d = new Date(ts * 1000);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatDateShort(ts) {
    if (!ts) return "";
    const d = new Date(ts * 1000);
    return `${d.getMonth() + 1}/${d.getDate()}/${d.getFullYear()}`;
}

// ===== LOADING =====
function showLoading() {
    document.getElementById('loadingOverlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

// ===== LOAD DATA =====
async function loadData(showLoadingIndicator = false) {
    if (isUpdating) return;
    if (showLoadingIndicator) showLoading();

    try {
        isUpdating = true;
        const res = await fetch(`/counterdashboard/api/data?_=${Date.now()}`, {
            headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' }
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (data.error) {
            showTableError(data.error);
            return;
        }

        // Update info cards
        const officeName = data.officeName || "N/A";
        const counterName = data.counterName || "N/A";
        
        document.getElementById("office").textContent = officeName;
        document.getElementById("counter").textContent = counterName;
        
        // Update sidebar
        const sideOfficeName = document.getElementById("sidebar-office-name");
        if (sideOfficeName) sideOfficeName.textContent = officeName;

        // Check if queue exists
        if (!data.hasQueue || !data.queueName) {
            // No queue assigned - show admin message
            const queueElement = document.getElementById("queue");
            queueElement.textContent = "⚠️ No Queue Assigned";
            queueElement.style.color = "#f59e0b";
            queueElement.style.fontWeight = "600";
            
            // Update serving banner
            const servingQueueEl = document.getElementById("servingQueue");
            if (servingQueueEl) servingQueueEl.textContent = "NO QUEUE ASSIGNED";
            
            // Show message in serving card
            document.getElementById("servingToken").textContent = "!--";
            document.getElementById("servingName").innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> No Queue Assigned';
            document.getElementById("servingMeta").innerHTML = 'Please contact your administrator to assign a queue to this counter';
            
            // Disable all action buttons
            document.getElementById("completeBtn").disabled = true;
            document.getElementById("skipBtn").disabled = true;
            document.getElementById("cancelBtn").disabled = true;
            
            // Show message in table
            const tbody = document.getElementById("tableBody");
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align:center; padding: 60px 20px;">
                        <div style="background: #fef3c7; border: 1px solid #fde68a; border-radius: 12px; padding: 40px; max-width: 500px; margin: 0 auto;">
                            <i class="fa-solid fa-building-user" style="font-size: 48px; color: #f59e0b; margin-bottom: 16px; display: inline-block;"></i>
                            <h3 style="color: #92400e; margin-bottom: 12px;">No Queue Assigned</h3>
                            <p style="color: #78350f; margin-bottom: 8px;">${data.message || "This counter doesn't have a queue assigned yet."}</p>
                            <p style="color: #78350f; font-size: 14px; margin-top: 16px;">
                                <i class="fa-solid fa-user-tie"></i> Please check with your administrator
                            </p>
                        </div>
                    </td>
                </tr>
            `;
            
            const now = new Date();
            document.getElementById("lastUpdateTime").textContent = now.toLocaleTimeString();
            lastUpdateTimestamp = now.getTime();
            return;
        }
        
        // Queue exists - normal flow
        const queueElement = document.getElementById("queue");
        queueElement.textContent = data.queueName;
        queueElement.style.color = ""; // Reset color
        queueElement.style.fontWeight = "";
        
        // Update serving banner queue label
        const servingQueueEl = document.getElementById("servingQueue");
        if (servingQueueEl) servingQueueEl.textContent = data.queueName.toUpperCase();
        
        const tokens = data.tokens || [];
        renderTable(tokens);
        renderServingCard(tokens);
        
        // Enable buttons if tokens exist
        if (tokens.length > 0) {
            document.getElementById("completeBtn").disabled = false;
            document.getElementById("skipBtn").disabled = false;
            document.getElementById("cancelBtn").disabled = false;
        } else {
            document.getElementById("completeBtn").disabled = true;
            document.getElementById("skipBtn").disabled = true;
            document.getElementById("cancelBtn").disabled = true;
        }

        const now = new Date();
        document.getElementById("lastUpdateTime").textContent = now.toLocaleTimeString();
        lastUpdateTimestamp = now.getTime();

    } catch (err) {
        console.error("Load error:", err);
        showTableError(err.message);
    } finally {
        isUpdating = false;
        if (showLoadingIndicator) hideLoading();
        // Refresh scroll button state after table updates
        setTimeout(updateScrollButtonState, 100);
    }
}

// ===== RENDER SERVING CARD =====
function renderServingCard(tokens) {
    const tokenBadge  = document.getElementById("servingToken");
    const servingName = document.getElementById("servingName");
    const servingMeta = document.getElementById("servingMeta");
    const completeBtn = document.getElementById("completeBtn");
    const skipBtn     = document.getElementById("skipBtn");
    const cancelBtn   = document.getElementById("cancelBtn");

    // Find the actively serving token (first non-skipped, non-served)
    const serving = tokens.find(t => t.status !== "skipped" && t.status !== "served");

    if (!serving) {
        tokenBadge.textContent = "--";
        servingName.textContent = "No token currently serving";
        servingMeta.textContent = "Waiting for customers...";
        currentServingId = null;
        completeBtn.disabled = true;
        skipBtn.disabled = true;
        cancelBtn.disabled = true;
        return;
    }

    currentServingId = serving.id;

    tokenBadge.textContent = serving.tokenNumber || "--";
    servingName.textContent = `${counterName()} • ${serving.serviceName || "Service"}`;

    const startedAt = formatTimeShort(serving.bookedtime);
    servingMeta.textContent = `Service: ${serving.serviceName || "—"} • Started: ${startedAt}`;

    completeBtn.disabled = false;
    skipBtn.disabled = false;
    cancelBtn.disabled = false;
}

function counterName() {
    return document.getElementById("counter").textContent || "Counter";
}

// ===== RENDER TABLE =====
function renderTable(tokens) {
    const tbody = document.getElementById("tableBody");

    if (tokens.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:40px; color:#94a3b8;">No waiting tokens</td></tr>`;
        return;
    }

    let html = "";
    tokens.forEach((t, idx) => {
        let displayStatus = t.status || "waiting";
        const isFirst = idx === 0 && displayStatus !== "skipped" && displayStatus !== "served";
        const isSecond = idx === 1 && displayStatus === "waiting";

        if (isFirst)  displayStatus = "serving";
        if (isSecond) displayStatus = "next";

        const rowClass = isFirst ? "row-serving" : isSecond ? "row-next" : "";
        const tokenClass = isFirst ? "token-link" : "token-link next-token";

        // Arrived cell
        let arrivedHtml = "";
        if (t.arrivedtime) {
            const arrivedClass = isFirst ? "arrived-time" : isSecond ? "arrived-time next" : "arrived-time";
            arrivedHtml = `<span class="${arrivedClass}">${formatTimeShort(t.arrivedtime)} ✓</span>`;
        } else {
            arrivedHtml = `<button class="set-arrival-btn" data-id="${t.id}">⏰ Set arrival</button>`;
        }

        // Booked cell
        const bookedHtml = `
            <div class="booked-cell">
                <span class="booked-time">${formatTimeShort(t.bookedtime)}</span>
                <span class="booked-date">${formatDateShort(t.bookedtime)}</span>
            </div>`;

        // Action buttons — disabled style for waiting rows
        const btnStyle = (displayStatus === "waiting" || displayStatus === "skipped") 
            ? ' style="opacity:0.4"' : '';

        html += `
        <tr class="${rowClass}">
            <td>${idx + 1}</td>
            <td><span class="${tokenClass}">${t.tokenNumber || "—"}</span></td>
            <td>${t.serviceName || "—"}</td>
            <td>${bookedHtml}</td>
            <td class="arrival-cell" data-id="${t.id}">${arrivedHtml}</td>
            <td><span class="badge ${displayStatus}">${capitalise(displayStatus)}</span></td>
            <td>
                <div class="tbl-actions">
                    <button class="icon-btn serve" onclick="actionToken('serve','${t.id}')" title="Serve / Complete"${btnStyle}>
                        <i class="fa-solid fa-check"></i>
                    </button>
                    <button class="icon-btn skip" onclick="actionToken('skip','${t.id}')" title="Skip"${btnStyle}>
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
            </td>
        </tr>`;
    });

    tbody.innerHTML = html;

    // Bind arrival click
    tbody.querySelectorAll('.set-arrival-btn').forEach(btn => {
        btn.addEventListener('click', e => {
            currentTokenId = e.currentTarget.getAttribute('data-id');
            openArrivalModal();
        });
    });
}

function capitalise(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function showTableError(msg) {
    document.getElementById("tableBody").innerHTML = `
        <tr><td colspan="7" style="text-align:center; padding:40px; color:#e11d48;">
            Error: ${msg}
        </td></tr>`;
}

// ===== SERVING CARD ACTIONS =====
window.serveCurrentToken = async function () {
    if (!currentServingId) return;
    await actionToken('serve', currentServingId);
};

window.skipCurrentToken = async function () {
    if (!currentServingId) return;
    await actionToken('skip', currentServingId);
};

window.cancelCurrentToken = async function () {
    // Cancel = same as skip in the backend for now
    if (!currentServingId) return;
    await actionToken('skip', currentServingId);
};

// ===== TOKEN ACTIONS =====
window.actionToken = async function (action, tokenId) {
    showLoading();
    try {
        const res = await fetch(`/counterdashboard/api/${action}/${tokenId}`, {
            method: "POST",
            headers: { 'Cache-Control': 'no-cache' }
        });
        if (res.ok) {
            await loadData(true);
        } else {
            const err = await res.json();
            alert(`Failed to ${action} token: ${err.error || "Unknown error"}`);
        }
    } catch (err) {
        alert(`Network error: ${err.message}`);
    } finally {
        hideLoading();
    }
};

// ===== ARRIVAL MODAL =====
function openArrivalModal() {
    const tz = "Asia/Colombo";
    const colomboTime = new Date().toLocaleTimeString('en-US', { timeZone: tz, hour12: false });
    const [h, m] = colomboTime.split(':');
    document.getElementById("arrivalTimeInput").value = `${h.padStart(2,'0')}:${m.padStart(2,'0')}`;
    const modal = document.getElementById("arrivalModal");
    modal.style.display = "flex";
}

function closeArrivalModal() {
    document.getElementById("arrivalModal").style.display = "none";
    currentTokenId = null;
}

async function saveArrival() {
    if (!currentTokenId) return;
    const timeStr = document.getElementById("arrivalTimeInput").value;
    if (!timeStr) return;

    showLoading();
    try {
        const tz = "Asia/Colombo";
        const now = new Date();
        const formatter = new Intl.DateTimeFormat('en-CA', {
            timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit'
        });
        let year, month, day;
        for (const p of formatter.formatToParts(now)) {
            if (p.type === 'year') year = p.value;
            if (p.type === 'month') month = p.value;
            if (p.type === 'day') day = p.value;
        }
        const dt = new Date(`${year}-${month}-${day}T${timeStr}:00`);
        const utcTs = dt.getTime() / 1000;

        const res = await fetch(`/counterdashboard/api/arrive/${currentTokenId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ arrivedtime: utcTs })
        });

        if (res.ok) {
            closeArrivalModal();
            await loadData(true);
        } else {
            const err = await res.json();
            alert("Failed to save: " + (err.error || "Unknown error"));
        }
    } catch (err) {
        alert("Error: " + err.message);
    } finally {
        hideLoading();
    }
}

// ===== AUTO REFRESH =====
function startAutoRefresh() {
    if (updateInterval) clearInterval(updateInterval);
    updateInterval = setInterval(() => loadData(false), 3000);
}

function stopAutoRefresh() {
    if (updateInterval) { clearInterval(updateInterval); updateInterval = null; }
}

// ===== CONNECTION STATUS =====
setInterval(() => {
    const age = Date.now() - lastUpdateTimestamp;
    const el = document.getElementById('updateStatus');
    if (!el) return;
    if (age > 10000) {
        el.textContent = '⚠️ Connection issue';
        el.style.background = '#ffcdd2';
        el.style.color = '#c62828';
    } else if (age > 5000) {
        el.textContent = '⏳ Updating...';
        el.style.background = '#fff3e0';
        el.style.color = '#e65100';
    } else {
        el.textContent = '✓ Auto-refresh ON';
        el.style.background = '#c8f7c5';
        el.style.color = '#1e7a34';
    }
}, 1000);

// ===== EVENT LISTENERS =====
document.getElementById("saveArrivalBtn").addEventListener("click", saveArrival);
document.getElementById("cancelArrivalBtn").addEventListener("click", closeArrivalModal);
window.addEventListener("click", e => {
    if (e.target === document.getElementById("arrivalModal")) closeArrivalModal();
});
window.addEventListener('beforeunload', stopAutoRefresh);

// ===== INIT =====
loadData(true);
startAutoRefresh();