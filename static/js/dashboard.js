// ================= DECODE HTML =================
function decodeHTML(str) {
    const txt = document.createElement("textarea");
    txt.innerHTML = str;
    return txt.value;
}

// ================= CLOCK + GREETING + STATUS =================
function updateClock() {
    const now = new Date();

    const optionsTime = {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true,
        timeZone: 'Asia/Colombo'
    };

    const optionsDate = {
        day: '2-digit',
        month: 'long',
        year: 'numeric',
        timeZone: 'Asia/Colombo'
    };

    const timeString = now.toLocaleTimeString('en-US', optionsTime);
    const dateString = now.toLocaleDateString('en-GB', optionsDate);

    const colomboHour = new Date(
        now.toLocaleString("en-US", { timeZone: "Asia/Colombo" })
    ).getHours();

    const clockEl = document.getElementById("live-clock");
    const dateEl = document.getElementById("current-date");
    if (clockEl) clockEl.innerText = timeString;
    if (dateEl) dateEl.innerText = dateString;

    let greet = "Good Evening";
    if (colomboHour < 12) greet = "Good Morning";
    else if (colomboHour < 17) greet = "Good Afternoon";

    const cleanOfficeName = decodeHTML(OFFICE_NAME || "");
    const greetingEl = document.getElementById("greeting-title");
    if (greetingEl) greetingEl.innerText = `${greet}, ${cleanOfficeName}`;

    // Status button
    const statusBtn = document.getElementById("status-btn");
    const statusText = document.getElementById("status-text");
    if (statusBtn && statusText) {
        const isOpen = isOfficeOpen(now);
        if (isOpen) {
            statusText.innerText = "Office Open";
            statusBtn.classList.remove("closed");
            statusBtn.classList.add("open");
        } else {
            statusText.innerText = "Office Closed";
            statusBtn.classList.remove("open");
            statusBtn.classList.add("closed");
        }
    }
}

function isOfficeOpen(now) {
    const openTimeStr = document.getElementById("modal-open-time-input")?.value || OPEN_TIME;
    const closeTimeStr = document.getElementById("modal-close-time-input")?.value || CLOSE_TIME;
    if (!openTimeStr || !closeTimeStr) return false;

    const [openH, openM] = openTimeStr.split(":").map(Number);
    const [closeH, closeM] = closeTimeStr.split(":").map(Number);

    const colomboNow = new Date(
        now.toLocaleString("en-US", { timeZone: "Asia/Colombo" })
    );

    const open = new Date(colomboNow);
    open.setHours(openH, openM, 0);
    const close = new Date(colomboNow);
    close.setHours(closeH, closeM, 0);

    return colomboNow >= open && colomboNow < close;
}

// ================= GLOBAL STATE =================
let currentFilter = "all";
let currentSearch = "";
let queuesData = [];

// ================= FETCH REAL-TIME DATA =================
async function fetchDashboardData(showLoading = false) {
    const container = document.getElementById("queue-table-container");
    
    // Show Lottie animation only if explicitly requested (e.g., manual refresh)
    if (showLoading) {
        container.innerHTML = `<div class="loading-animation">
            <dotlottie-wc src="https://lottie.host/6f8832dc-2f7e-431f-ac9e-62106e5cfc1e/Ve1fxiZCLe.lottie" style="width: 200px; height: 200px;" autoplay loop></dotlottie-wc>
            <p>Loading queues...</p>
        </div>`;
    }

    try {
        const response = await fetch("/dashboard/api/data");
        if (!response.ok) throw new Error("Failed to fetch");
        const data = await response.json();

        // Update stats
        document.getElementById("tokens-today").innerText = data.tokens_today;
        document.getElementById("waiting-count").innerText = data.waiting_count;
        document.getElementById("served-count").innerText = data.served_count;
        document.getElementById("counters-count").innerText = data.counters_count;

        // Update office name in greeting (if changed)
        if (data.office_name && data.office_name !== OFFICE_NAME) {
            const cleanName = decodeHTML(data.office_name);
            const greet = document.getElementById("greeting-title").innerText.split(",")[0];
            document.getElementById("greeting-title").innerText = `${greet}, ${cleanName}`;
            window.OFFICE_NAME = data.office_name;
        }

        // Update open/close times in modal inputs
        const openInput = document.getElementById("modal-open-time-input");
        const closeInput = document.getElementById("modal-close-time-input");
        if (openInput && !openInput.disabled) {
            if (data.open_time) openInput.value = data.open_time;
            if (data.close_time) closeInput.value = data.close_time;
        }

        // Update queues
        queuesData = data.queues || [];
        renderQueuesTable();

        // Update status badge
        updateClock();
    } catch (error) {
        console.error("Error fetching dashboard data:", error);
        if (showLoading) {
            container.innerHTML = `<div class="empty-state">
                <i class="fa-solid fa-circle-exclamation"></i>
                <p>Failed to load queues. Click refresh to try again.</p>
            </div>`;
        }
    }
}

// ================= QUEUE RENDERING WITH FILTER + SEARCH =================
function renderQueuesTable() {
    let filtered = getFilteredQueues();
    
    // Apply search filter
    if (currentSearch.trim() !== "") {
        const searchLower = currentSearch.toLowerCase();
        filtered = filtered.filter(q => q.name && q.name.toLowerCase().includes(searchLower));
    }

    const container = document.getElementById("queue-table-container");

    // Update tab counts (based on original queuesData, not filtered)
    const allCount = queuesData.length;
    const activeCount = queuesData.filter(q => q.status === "active").length;
    const inactiveCount = queuesData.filter(q => q.status !== "active").length;
    document.getElementById("all-count").innerText = allCount;
    document.getElementById("active-count").innerText = activeCount;
    document.getElementById("inactive-count").innerText = inactiveCount;

    if (filtered.length === 0) {
        container.innerHTML = `<div class="empty-state">
            <i class="fa-solid fa-layer-group"></i>
            <p>No queues match your search or filter.</p>
        </div>`;
        return;
    }

    // Build table with horizontal scroll wrapper
    let tableHtml = `<div class="table-wrapper">
        <table class="queue-table">
            <thead>
                <tr><th>Queue Name</th><th>Service</th><th>Counters</th><th>Daily Limit</th><th>Status</th></tr>
            </thead>
            <tbody>`;
    filtered.forEach(q => {
        const statusClass = q.status === "active" ? "active" : "inactive";
        const statusText = q.status === "active" ? "Active" : "Inactive";
        tableHtml += `<tr>
            <td>${escapeHtml(q.name)}</td>
            <td>${escapeHtml(q.service)}</td>
            <td>${escapeHtml(q.counters)}</td>
            <td>${q.limit || "—"}</td>
            <td><span class="status ${statusClass}">${statusText}</span></td>
        </tr>`;
    });
    tableHtml += `</tbody>
        </table>
    </div>`;
    container.innerHTML = tableHtml;
}

function getFilteredQueues() {
    if (currentFilter === "active") {
        return queuesData.filter(q => q.status === "active");
    } else if (currentFilter === "inactive") {
        return queuesData.filter(q => q.status !== "active");
    }
    return queuesData;
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/[&<>]/g, function(m) {
        if (m === "&") return "&amp;";
        if (m === "<") return "&lt;";
        if (m === ">") return "&gt;";
        return m;
    });
}

// ================= LIVE SEARCH (triggers on every keystroke) =================
function setupSearch() {
    const searchInput = document.getElementById("queue-search");
    const searchBtn = document.getElementById("search-btn");

    const performSearch = () => {
        currentSearch = searchInput ? searchInput.value : "";
        renderQueuesTable();
    };

    // Live search: trigger on every input (typing, pasting, deleting)
    if (searchInput) {
        searchInput.addEventListener("input", performSearch);
        // Also allow Enter key for convenience
        searchInput.addEventListener("keyup", (e) => {
            if (e.key === "Enter") performSearch();
        });
    }

    // Keep the search button (if exists) for manual trigger
    if (searchBtn) {
        searchBtn.addEventListener("click", performSearch);
    }
}

// ================= MANUAL REFRESH =================
function setupManualRefresh() {
    const refreshBtn = document.getElementById("manual-refresh-btn");
    if (refreshBtn) {
        refreshBtn.addEventListener("click", () => {
            fetchDashboardData(true); // Show loading animation
        });
    }
}

// ================= MODAL EDITING =================
async function saveOfficeHours() {
    const openTime = document.getElementById("modal-open-time-input").value;
    const closeTime = document.getElementById("modal-close-time-input").value;
    const messageDiv = document.getElementById("modal-message");

    if (!openTime || !closeTime) {
        messageDiv.style.color = "red";
        messageDiv.innerText = "Please fill both fields";
        return;
    }

    try {
        const response = await fetch("/dashboard/update_hours", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ openTime, closeTime })
        });
        const result = await response.json();
        if (result.success) {
            messageDiv.style.color = "green";
            messageDiv.innerText = "Hours updated successfully!";
            setTimeout(() => { messageDiv.innerText = ""; }, 2000);
            // Refresh data immediately
            await fetchDashboardData(false);
            // Close modal after short delay
            setTimeout(() => {
                document.getElementById("office-modal").style.display = "none";
            }, 1000);
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        messageDiv.style.color = "red";
        messageDiv.innerText = "Error saving: " + error.message;
    }
}

function setupModal() {
    const statusBtn = document.getElementById("status-btn");
    const modal = document.getElementById("office-modal");
    const closeBtn = document.getElementById("close-modal");
    const saveBtn = document.getElementById("save-hours-btn");

    // Set initial input values from server
    const openInput = document.getElementById("modal-open-time-input");
    const closeInput = document.getElementById("modal-close-time-input");
    if (OPEN_TIME) openInput.value = OPEN_TIME;
    if (CLOSE_TIME) closeInput.value = CLOSE_TIME;

    if (statusBtn && modal) {
        statusBtn.addEventListener("click", () => {
            modal.style.display = "flex";
        });
    }

    if (closeBtn && modal) {
        closeBtn.addEventListener("click", () => {
            modal.style.display = "none";
        });
    }

    if (saveBtn) {
        saveBtn.addEventListener("click", saveOfficeHours);
    }

    window.addEventListener("click", (e) => {
        if (e.target === modal) {
            modal.style.display = "none";
        }
    });
}

// ================= QUEUE FILTER TABS =================
function setupQueueTabs() {
    const tabs = document.querySelectorAll(".tab");
    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            currentFilter = tab.getAttribute("data-filter");
            renderQueuesTable();
        });
    });
}

// ================= INITIALIZE =================
document.addEventListener("DOMContentLoaded", () => {
    setupModal();
    setupQueueTabs();
    setupSearch();
    setupManualRefresh();
    
    // Initial load (no animation)
    fetchDashboardData(false);
    
    // Poll every 3 seconds for real-time updates (no loading animation on auto-refresh)
    setInterval(() => fetchDashboardData(false), 3000);
    setInterval(updateClock, 1000);
    updateClock();
});