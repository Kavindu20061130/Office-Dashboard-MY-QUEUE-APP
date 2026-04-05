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

    // Use Colombo hour (IMPORTANT FIX)
    const colomboHour = new Date(
        now.toLocaleString("en-US", { timeZone: "Asia/Colombo" })
    ).getHours();

    // Set time & date safely
    const clockEl = document.getElementById("live-clock");
    const dateEl = document.getElementById("current-date");

    if (clockEl) clockEl.innerText = timeString;
    if (dateEl) dateEl.innerText = dateString;

    // Greeting
    let greet = "Good Evening";
    if (colomboHour < 12) greet = "Good Morning";
    else if (colomboHour < 17) greet = "Good Afternoon";

    const cleanOfficeName = decodeHTML(OFFICE_NAME || "");
    const greetingEl = document.getElementById("greeting-title");

    if (greetingEl) {
        greetingEl.innerText = `${greet}, ${cleanOfficeName}`;
    }

    // STATUS
    const statusBtn = document.getElementById("status-btn");
    const statusText = document.getElementById("status-text");

    if (!statusBtn || !statusText) return;

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

// ================= OFFICE TIME CHECK =================
function isOfficeOpen(now) {
    if (!OPEN_TIME || !CLOSE_TIME) return false;

    const [openH, openM] = OPEN_TIME.split(":").map(Number);
    const [closeH, closeM] = CLOSE_TIME.split(":").map(Number);

    const colomboNow = new Date(
        now.toLocaleString("en-US", { timeZone: "Asia/Colombo" })
    );

    const open = new Date(colomboNow);
    open.setHours(openH, openM, 0);

    const close = new Date(colomboNow);
    close.setHours(closeH, closeM, 0);

    return colomboNow >= open && colomboNow < close;
}

// ================= MODAL =================
document.addEventListener("DOMContentLoaded", () => {
    const statusBtn = document.getElementById("status-btn");
    const modal = document.getElementById("office-modal");
    const closeBtn = document.getElementById("close-modal");

    const openEl = document.getElementById("modal-open-time");
    const closeEl = document.getElementById("modal-close-time");

    if (openEl) openEl.innerText = OPEN_TIME || "Not set";
    if (closeEl) closeEl.innerText = CLOSE_TIME || "Not set";

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

    window.addEventListener("click", (e) => {
        if (e.target === modal) {
            modal.style.display = "none";
        }
    });
});

// ================= RUN CLOCK =================
setInterval(updateClock, 1000);
updateClock();