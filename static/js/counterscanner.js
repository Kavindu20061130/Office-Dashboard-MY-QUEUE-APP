// Global variables
let scannerInstance = null;
let currentCameraId = null;
let currentResolution = { width: 1280, height: 720 };
let scanInProgress = false;
let lastScannedText = '';
let lastScanTime = 0;
const SCAN_DEBOUNCE_MS = 2000;
let refreshInterval = null;
let audioContext = null;
let soundEnabled = true;

// Helper: initialize audio context
function initAudio() {
    if (audioContext) return;
    try {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        audioContext.resume();
    } catch(e) { console.warn("Audio init failed", e); }
}

// Play beep if sound enabled
function playBeep() {
    if (!soundEnabled) return;
    if (!audioContext) {
        initAudio();
        if (!audioContext) return;
    }
    audioContext.resume().then(() => {
        const osc = audioContext.createOscillator();
        const gain = audioContext.createGain();
        osc.connect(gain);
        gain.connect(audioContext.destination);
        osc.frequency.value = 880;
        gain.gain.value = 0.2;
        osc.start();
        gain.gain.exponentialRampToValueAtTime(0.00001, audioContext.currentTime + 0.3);
        osc.stop(audioContext.currentTime + 0.3);
    }).catch(e => console.warn("Audio resume failed", e));
}

// Toggle sound
function toggleSound() {
    soundEnabled = !soundEnabled;
    const btn = document.getElementById("soundToggleBtn");
    if (btn) {
        btn.innerHTML = soundEnabled ? 
            '<i class="fa-solid fa-volume-high"></i> Sound ON' : 
            '<i class="fa-solid fa-volume-xmark"></i> Sound OFF';
        btn.style.background = soundEnabled ? "#475569" : "#64748b";
    }
    if (soundEnabled) playBeep();
}

// Modal functions
function showModal(title, iconType, detailsHtml, extraHtml = "") {
    const modal = document.getElementById("tokenModal");
    const modalTitle = document.getElementById("modalTitle");
    const modalIcon = document.getElementById("modalIcon");
    const tokenDetailsDiv = document.getElementById("tokenDetails");
    const modalExtra = document.getElementById("modalExtra");

    modalTitle.innerText = title;
    if (iconType === "success") {
        modalIcon.style.background = "#10b981";
        modalIcon.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M20 6L9 17L4 12" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
    } else if (iconType === "error") {
        modalIcon.style.background = "#ef4444";
        modalIcon.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M18 6L6 18M6 6l12 12" stroke="white" stroke-width="3" stroke-linecap="round"/></svg>`;
    } else {
        modalIcon.style.background = "#6366f1";
        modalIcon.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 8v4l3 3M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z" stroke="white" stroke-width="2"/></svg>`;
    }
    tokenDetailsDiv.innerHTML = detailsHtml;
    modalExtra.innerHTML = extraHtml;
    modal.style.display = "flex";
}

function closeModal() {
    document.getElementById("tokenModal").style.display = "none";
}

function formatTime(seconds) {
    if (!seconds) return "Not set";
    const d = new Date(seconds * 1000);
    return d.toLocaleTimeString([], { hour: '2-digit', minute:'2-digit', second:'2-digit' });
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;'})[m]);
}

// Fetch counter/queue info and update UI
async function loadCounterInfo() {
    try {
        const res = await fetch("/counterdashboard/api/current-counter");
        const data = await res.json();
        if (data.error) return;
        document.getElementById("office").innerText = data.officeName || "—";
        document.getElementById("queue").innerText = data.queueName || "No queue assigned";
        document.getElementById("counter").innerText = data.counterName || "—";
        document.getElementById("sidebar-office-name").innerText = data.officeName || "";
        document.getElementById("sidebar-user-name").innerText = data.counterName || "Counter";
        const avatar = document.getElementById("userAvatar");
        if (avatar) avatar.innerText = (data.counterName || "C").charAt(0).toUpperCase();
        return data;
    } catch (e) {
        console.error("Failed to load counter info", e);
    }
}

// Fetch waiting tokens for this counter's queue
async function fetchWaitingTokens() {
    try {
        const res = await fetch("/counterdashboard/scanner/api/waiting-tokens");
        const data = await res.json();
        const container = document.getElementById("waitingTokensList");
        const searchTerm = document.getElementById("searchWaiting")?.value.toLowerCase() || "";
        
        if (!data.waiting || data.waiting.length === 0) {
            container.innerHTML = '<div class="loading">No waiting tokens</div>';
            return;
        }
        
        let filtered = data.waiting;
        if (searchTerm) {
            filtered = filtered.filter(t => 
                t.tokenNumber.toLowerCase().includes(searchTerm) || 
                t.serviceName.toLowerCase().includes(searchTerm)
            );
        }
        
        if (filtered.length === 0) {
            container.innerHTML = '<div class="loading">No matching tokens</div>';
            return;
        }
        
        container.innerHTML = filtered.map(t => `
            <div class="token-item ${t.arrivedtime ? 'arrived' : 'waiting'}">
                <div class="token-number">
                    ${escapeHtml(t.tokenNumber)}
                    <span class="badge ${t.arrivedtime ? 'badge-arrived' : 'badge-waiting'}">
                        ${t.arrivedtime ? 'Arrived' : 'Waiting'}
                    </span>
                </div>
                <div class="token-service">${escapeHtml(t.serviceName)}</div>
                ${t.arrivedtime ? `<div class="token-time">Arrived: ${formatTime(t.arrivedtime)}</div>` : ''}
            </div>
        `).join('');
    } catch (e) {
        console.error("Failed to fetch waiting tokens", e);
        document.getElementById("waitingTokensList").innerHTML = '<div class="error-text">Error loading tokens</div>';
    }
}

// Process a token scan (arrive or serve)
async function processScan(tokenId) {
    if (scanInProgress) return;
    scanInProgress = true;
    try {
        // First get token info (also validates it belongs to this counter's queue)
        const infoRes = await fetch(`/counterdashboard/scanner/api/token-info/${encodeURIComponent(tokenId)}`);
        const info = await infoRes.json();
        if (!infoRes.ok) throw new Error(info.error);
        
        if (info.status === "served") {
            showModal("Already Served", "error", `<div class="error-text">Token "${escapeHtml(tokenId)}" was already served.</div>`);
            return;
        }
        
        if (info.arrivedtime) {
            // Second scan -> serve
            const serveRes = await fetch("/counterdashboard/scanner/api/serve", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ tokenId })
            });
            const serveData = await serveRes.json();
            if (!serveRes.ok) throw new Error(serveData.error);
            
            const detailsHtml = `<div class="wait-time">⏱️ Waiting time: <strong>${escapeHtml(serveData.waitTime)}</strong></div>`;
            showModal("🎉 Service Completed", "success", detailsHtml, "Token marked as served.");
        } else {
            // First scan -> arrive
            const arriveRes = await fetch("/counterdashboard/scanner/api/arrive", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ tokenId })
            });
            const arriveData = await arriveRes.json();
            if (!arriveRes.ok) throw new Error(arriveData.error);
            
            const token = arriveData.token;
            const detailsHtml = `
                <div class="detail-row"><span class="detail-label">Token Number</span><span class="detail-value">${escapeHtml(token.tokenNumber)}</span></div>
                <div class="detail-row"><span class="detail-label">Service</span><span class="detail-value">${escapeHtml(token.serviceName)}</span></div>
                <div class="detail-row"><span class="detail-label">Queue</span><span class="detail-value">${escapeHtml(token.queueName)}</span></div>
                <div class="detail-row"><span class="detail-label">Arrived Time</span><span class="detail-value">${formatTime(token.arrivedtime)}</span></div>
            `;
            showModal("✅ Arrival Recorded", "success", detailsHtml, "Scan again to complete service.");
        }
        
        fetchWaitingTokens(); // refresh list
    } catch (err) {
        showModal("Error", "error", `<div class="error-text">${escapeHtml(err.message)}</div>`);
    } finally {
        scanInProgress = false;
    }
}

// QR scan callback
async function onScanSuccess(decodedText) {
    const now = Date.now();
    const tokenId = decodedText.trim();
    if (!tokenId) return;
    
    playBeep();
    
    if (tokenId === lastScannedText && (now - lastScanTime) < SCAN_DEBOUNCE_MS) {
        console.log(`Debounced duplicate of ${tokenId}`);
        return;
    }
    lastScannedText = tokenId;
    lastScanTime = now;
    await processScan(tokenId);
}

function onScanError(err) {
    if (err && (err.includes("NotFoundException") || err.includes("NoMultiFormatReaders"))) return;
    console.warn(err);
}

// Camera handling
async function getCameraDevices() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        initAudio(); // user gesture
        stream.getTracks().forEach(t => t.stop());
        const devices = await navigator.mediaDevices.enumerateDevices();
        return devices.filter(d => d.kind === 'videoinput');
    } catch (err) {
        showModal("Camera Error", "error", `<div class="error-text">Camera access denied or no camera found.</div>`);
        return [];
    }
}

async function populateCameraSelect() {
    const select = document.getElementById('cameraSelect');
    select.innerHTML = '<option value="">Loading...</option>';
    const devices = await getCameraDevices();
    select.innerHTML = '';
    if (devices.length === 0) {
        select.innerHTML = '<option value="">No camera found</option>';
        return;
    }
    devices.forEach((device, idx) => {
        const option = document.createElement('option');
        option.value = device.deviceId;
        option.text = device.label || `Camera ${idx + 1}`;
        if (idx === 0) option.selected = true;
        select.appendChild(option);
    });
    currentCameraId = devices[0]?.deviceId || null;
    if (currentCameraId) restartScanner();
}

function updateResolution() {
    const resSelect = document.getElementById('resolutionSelect');
    const [w, h] = resSelect.value.split('x').map(Number);
    currentResolution = { width: w, height: h };
    restartScanner();
}

async function startScanner() {
    const readerElement = document.getElementById("reader");
    if (!readerElement) return;
    if (scannerInstance) {
        await scannerInstance.stop();
        readerElement.innerHTML = "";
    }
    const html5QrCode = new Html5Qrcode("reader");
    const config = {
        fps: 15,
        qrbox: { width: 300, height: 300 },
        aspectRatio: currentResolution.width / currentResolution.height,
        videoConstraints: {
            deviceId: currentCameraId ? { exact: currentCameraId } : undefined,
            width: { ideal: currentResolution.width },
            height: { ideal: currentResolution.height },
            facingMode: currentCameraId ? undefined : "environment"
        }
    };
    try {
        await html5QrCode.start(
            currentCameraId ? { deviceId: { exact: currentCameraId } } : { facingMode: "environment" },
            config,
            onScanSuccess,
            onScanError
        );
        scannerInstance = html5QrCode;
    } catch (err) {
        console.error("Camera start error", err);
        showModal("Camera Error", "error", `<div class="error-text">Failed to start camera. Try another camera or resolution.</div>`);
    }
}

function restartScanner() {
    if (scannerInstance) {
        scannerInstance.stop().then(() => startScanner()).catch(() => startScanner());
    } else {
        startScanner();
    }
}

function manualScan() {
    const tokenId = document.getElementById('manualTokenId').value.trim();
    if (!tokenId) {
        showModal("Error", "error", "<div class='error-text'>Please enter a token ID</div>");
        return;
    }
    processScan(tokenId);
}

// Initialization
window.addEventListener("load", async () => {
    await loadCounterInfo();
    await populateCameraSelect();
    await startScanner();
    await fetchWaitingTokens();
    
    refreshInterval = setInterval(fetchWaitingTokens, 8000); // refresh list every 8 sec
    
    document.getElementById("modalCloseBtn").addEventListener("click", closeModal);
    document.getElementById("cameraSelect").addEventListener("change", (e) => {
        currentCameraId = e.target.value;
        restartScanner();
    });
    document.getElementById("resolutionSelect").addEventListener("change", updateResolution);
    document.getElementById("manualScanBtn").addEventListener("click", manualScan);
    document.getElementById("soundToggleBtn").addEventListener("click", toggleSound);
    document.getElementById("searchWaiting").addEventListener("input", fetchWaitingTokens);
});

window.addEventListener("beforeunload", () => {
    if (refreshInterval) clearInterval(refreshInterval);
    if (scannerInstance) scannerInstance.stop();
});