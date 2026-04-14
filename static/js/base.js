// static/js/base.js

// Auto-hide flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.remove();
            }, 300);
        }, 5000);
    });
});

// Function to show toast notifications (reusable)
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast') || createToastContainer();
    toast.textContent = message;
    toast.className = `toast t-${type} show`;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function createToastContainer() {
    const toast = document.createElement('div');
    toast.id = 'toast';
    toast.className = 'toast';
    document.body.appendChild(toast);
    return toast;
}

// Add toast styles dynamically (polished, no color changes)
const toastStyles = `
.toast {
    position: fixed;
    bottom: 28px;
    right: 28px;
    background: #1e293b;
    color: white;
    padding: 12px 22px;
    border-radius: 40px;
    font-size: 0.85rem;
    font-weight: 500;
    box-shadow: 0 20px 40px -8px rgba(0, 0, 0, 0.25);
    transform: translateY(20px);
    opacity: 0;
    transition: all 0.35s cubic-bezier(0.2, 0.9, 0.4, 1);
    z-index: 99999;
    backdrop-filter: blur(8px);
    border: 0.5px solid rgba(255, 255, 255, 0.08);
}
.toast.show {
    transform: translateY(0);
    opacity: 1;
}
.toast.t-success {
    background: #147a33;
}
.toast.t-error {
    background: #e11d48;
}
`;

const styleSheet = document.createElement("style");
styleSheet.textContent = toastStyles;
document.head.appendChild(styleSheet);