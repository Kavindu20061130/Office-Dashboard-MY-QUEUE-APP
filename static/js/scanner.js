// Global variables
let scannerInstance = null;
let currentCameraId = null;
let currentResolution = { width: 1280, height: 720 };
let scanInProgress = false;
let lastScannedText = '';
let lastScanTime = 0;
const SCAN_DEBOUNCE_MS = 2000;
let refreshInterval = null;
let availableCameras = [];
let audioContext = null;
let soundEnabled = true;      // Sound ON by default

// Initialize audio context (only after user interaction)
function initAudio() {
    if (audioContext) return;
    try {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        audioContext.resume();
        console.log("Audio context initialised");
    } catch(e) { console.warn("Audio init failed", e); }
}

// Play beep – only if soundEnabled
function playBeep() {
    if (!soundEnabled) return;
    if (!audioContext) {
        initAudio();
        if (!audioContext) return;
    }
    audioContext.resume().then(() => {
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        oscillator.frequency.value = 880;
        gainNode.gain.value = 0.2;
        oscillator.start();
        gainNode.gain.exponentialRampToValueAtTime(0.00001, audioContext.currentTime + 0.3);
        oscillator.stop(audioContext.currentTime + 0.3);
    }).catch(e => console.warn("Audio resume failed", e));
}

// Toggle sound on/off and update button UI
function toggleSound() {
    soundEnabled = !soundEnabled;
    const btn = document.getElementById("soundToggleBtn");
    if (btn) {
        if (soundEnabled) {
            btn.innerHTML = '<i class="fa-solid fa-volume-high"></i> Sound ON';
            btn.style.background = "#475569";
        } else {
            btn.innerHTML = '<i class="fa-solid fa-volume-xmark"></i> Sound OFF';
            btn.style.background = "#64748b";
        }
    }
    if (soundEnabled) playBeep();
}

// Helper: show modal (success/error/info)
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
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

// API calls
async function fetchAndRenderLists() {
    try {
        const waitRes = await fetch("/api/qr/waiting-tokens");
        if (!waitRes.ok) throw new Error("Failed to fetch waiting tokens");
        const waitData = await waitRes.json();
        const container = document.getElementById("waitingTokensList");
        const searchTerm = document.getElementById("searchWaiting")?.value.toLowerCase() || "";
        
        if (!waitData.waiting || waitData.waiting.length === 0) {
            container.innerHTML = '<div class="text-muted">No waiting tokens</div>';
        } else {
            let filtered = waitData.waiting;
            if (searchTerm) {
                filtered = filtered.filter(t => 
                    t.tokenNumber.toLowerCase().includes(searchTerm) || 
                    t.serviceName.toLowerCase().includes(searchTerm)
                );
            }
            if (filtered.length === 0) {
                container.innerHTML = '<div class="text-muted">No matching tokens</div>';
            } else {
                container.innerHTML = filtered.map(t => {
                    let badgeClass = '';
                    let badgeText = '';
                    let extraHtml = '';
                    
                    // Check if token is cancelled
                    if (t.status === 'cancelled') {
                        badgeClass = 'badge-cancelled';
                        badgeText = 'Cancelled';
                        // No arrival time shown for cancelled tokens
                    } else if (t.arrivedTime) {
                        badgeClass = 'badge-arrived';
                        badgeText = 'Arrived';
                        extraHtml = `<div class="token-time">Arrived: ${formatTime(t.arrivedTime)}</div>`;
                    } else {
                        badgeClass = 'badge-waiting';
                        badgeText = 'Waiting';
                    }
                    
                    return `
                        <div class="token-item ${t.arrivedTime ? 'arrived' : 'waiting'} ${t.status === 'cancelled' ? 'cancelled' : ''}">
                            <div class="token-number">
                                ${escapeHtml(t.tokenNumber)}
                                <span class="badge ${badgeClass}">${badgeText}</span>
                            </div>
                            <div class="token-service">${escapeHtml(t.serviceName)}</div>
                            ${extraHtml}
                        </div>
                    `;
                }).join('');
            }
        }

        const recentRes = await fetch("/api/qr/recent-scans");
        if (!recentRes.ok) throw new Error("Failed to fetch recent scans");
        const recentData = await recentRes.json();
        const recentContainer = document.getElementById("recentScansList");
        if (!recentData.recent || recentData.recent.length === 0) {
            recentContainer.innerHTML = '<div class="text-muted">No recent scans</div>';
        } else {
            recentContainer.innerHTML = recentData.recent.map(t => `
                <div class="token-item" style="border-left-color: #94a3b8;">
                    <div class="token-number">${escapeHtml(t.tokenNumber)}</div>
                    <div class="token-service">${escapeHtml(t.serviceName)}</div>
                    ${t.servedTime ? `<div class="token-time">Served: ${formatTime(t.servedTime)}</div>` : ''}
                </div>
            `).join('');
        }
    } catch (err) {
        console.error(err);
        document.getElementById("waitingTokensList").innerHTML = '<div class="error-text">Error loading waiting tokens</div>';
        document.getElementById("recentScansList").innerHTML = '<div class="error-text">Error loading recent scans</div>';
    }
}

// Token operations
async function getTokenInfo(tokenId) {
    const response = await fetch(`/api/qr/token-info/${encodeURIComponent(tokenId)}`);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error);
    return result;
}

async function handleFirstScan(tokenId) {
    const response = await fetch("/api/qr/arrive", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tokenId: tokenId })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error);
    return result;
}

async function handleSecondScan(tokenId) {
    const response = await fetch("/api/qr/serve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tokenId: tokenId })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error);
    return result;
}

async function processScan(tokenId) {
    if (scanInProgress) return;
    scanInProgress = true;
    try {
        const info = await getTokenInfo(tokenId);
        
        // ❌ Check for cancelled token first
        if (info.status === "cancelled") {
            showModal(
                "Cancelled Token",
                "error",
                `<div class="error-text">This token is cancelled. Service cannot be provided. Please book another.</div>`
            );
            return;
        }
        
        if (info.status === "served") {
            showModal("Already Served", "error", `<div class="error-text">Token "${escapeHtml(tokenId)}" was already served.</div>`);
            return;
        }
        
        if (info.arrivedTime) {
            const serveResult = await handleSecondScan(tokenId);
            const waitTime = serveResult.waitTime || "calculated";
            const detailsHtml = `<div class="wait-time">⏱️ Waiting time: <strong>${escapeHtml(waitTime)}</strong></div>`;
            showModal("🎉 Service Completed", "success", detailsHtml, "Analytics saved.");
            fetchAndRenderLists();
        } else {
            const arriveResult = await handleFirstScan(tokenId);
            const token = arriveResult.token;
            const detailsHtml = `
                <div class="detail-row"><span class="detail-label">Token Number</span><span class="detail-value">${escapeHtml(token.tokenNumber)}</span></div>
                <div class="detail-row"><span class="detail-label">Service</span><span class="detail-value">${escapeHtml(token.serviceName)}</span></div>
                <div class="detail-row"><span class="detail-label">Queue</span><span class="detail-value">${escapeHtml(token.queueName)} (${escapeHtml(token.queueType)})</span></div>
                <div class="detail-row"><span class="detail-label">Arrived Time</span><span class="detail-value">${formatTime(token.arrivedTime)}</span></div>
            `;
            showModal("✅ Arrival Recorded", "success", detailsHtml, "Scan again to complete service.");
            fetchAndRenderLists();
        }
    } catch (err) {
        showModal("Error", "error", `<div class="error-text">${escapeHtml(err.message)}</div>`);
    } finally {
        scanInProgress = false;
    }
}

// QR scan callback – plays beep on every scan (if sound enabled)
async function onScanSuccess(decodedText) {
    const now = Date.now();
    const tokenId = decodedText.trim();
    if (!tokenId) return;

    playBeep();   // sound on every QR detection

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

// Camera device handling with error modal
async function getCameraDevices() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        initAudio();
        stream.getTracks().forEach(track => track.stop());
        const devices = await navigator.mediaDevices.enumerateDevices();
        return devices.filter(device => device.kind === 'videoinput');
    } catch (err) {
        console.error("Camera permission error", err);
        showModal("Camera Error", "error", `<div class="error-text">${err.message || "Camera access denied or no camera found."}</div>`);
        return [];
    }
}

async function populateCameraSelect() {
    const select = document.getElementById('cameraSelect');
    select.innerHTML = '<option value="">Loading cameras...</option>';
    const devices = await getCameraDevices();
    availableCameras = devices;
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

// Resolution handling (default HD)
function updateResolution() {
    const resSelect = document.getElementById('resolutionSelect');
    const [width, height] = resSelect.value.split('x').map(Number);
    currentResolution = { width, height };
    restartScanner();
}

// Start/stop scanner with error handling for failed camera
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
        showModal("Camera Error", "error", `<div class="error-text">Failed to start camera: ${escapeHtml(err.message || err)}. Please check your camera connection or select another camera.</div>`);
        try {
            await html5QrCode.start({ facingMode: "environment" }, config, onScanSuccess, onScanError);
            scannerInstance = html5QrCode;
            showModal("Info", "info", "<div>Switched to default camera.</div>");
        } catch (err2) {
            console.error("Fallback camera also failed", err2);
        }
    }
}

function restartScanner() {
    if (scannerInstance) {
        scannerInstance.stop().then(() => startScanner()).catch(() => startScanner());
    } else {
        startScanner();
    }
}

// Manual scan
function manualScan() {
    const tokenId = document.getElementById('manualTokenId').value.trim();
    if (!tokenId) {
        showModal("Error", "error", "<div class='error-text'>Please enter a token ID</div>");
        return;
    }
    processScan(tokenId);
}

// Event listeners and initialization
window.addEventListener("load", async () => {
    await populateCameraSelect();
    await startScanner();
    await fetchAndRenderLists();
    refreshInterval = setInterval(fetchAndRenderLists, 5000);
    document.getElementById("modalCloseBtn").addEventListener("click", closeModal);
    document.getElementById("cameraSelect").addEventListener("change", (e) => {
        currentCameraId = e.target.value;
        restartScanner();
    });
    document.getElementById("resolutionSelect").addEventListener("change", updateResolution);
    document.getElementById("manualScanBtn").addEventListener("click", manualScan);
    const soundBtn = document.getElementById("soundToggleBtn");
    if (soundBtn) soundBtn.addEventListener("click", toggleSound);
    document.getElementById("searchWaiting").addEventListener("input", () => fetchAndRenderLists());
});

window.addEventListener("beforeunload", () => {
    if (refreshInterval) clearInterval(refreshInterval);
    if (scannerInstance) scannerInstance.stop();
});