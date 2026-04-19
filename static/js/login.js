/**
 * Login Page Controller
 * Professional implementation with modular pattern and event delegation
 */
(function() {
    'use strict';

    // ==========================
    // DOM Elements Cache
    // ==========================
    const DOM = {
        officeSelect: null,
        officeIdDisplay: null,
        roleCounter: null,
        roleAdmin: null,
        userRoleInput: null,
        userInput: null,
        passwordField: null,
        loginTitle: null,
        loginSubtitle: null,
        submitBtn: null,
        userLabel: null,
        infoAlert: null,
        loginForm: null          // <-- added reference to the form
    };

    // ==========================
    // Utility Functions
    // ==========================
    const utils = {
        getElement(id) {
            const el = document.getElementById(id);
            if (!el) console.warn(`Element with id "${id}" not found`);
            return el;
        },

        injectCloseButtonStyles() {
            if (document.getElementById('flash-close-styles')) return;
            const style = document.createElement('style');
            style.id = 'flash-close-styles';
            style.textContent = `
                .custom-success, .custom-error {
                    position: relative;
                    padding-right: 35px !important;
                }
                .flash-close-btn {
                    position: absolute;
                    top: 50%;
                    right: 12px;
                    transform: translateY(-50%);
                    cursor: pointer;
                    font-size: 20px;
                    font-weight: bold;
                    color: inherit;
                    opacity: 0.7;
                    transition: opacity 0.2s;
                    line-height: 1;
                }
                .flash-close-btn:hover {
                    opacity: 1;
                }
            `;
            document.head.appendChild(style);
        },

        removeFlashMessage(flashElement) {
            flashElement.style.transition = 'opacity 0.3s ease';
            flashElement.style.opacity = '0';
            setTimeout(() => flashElement.remove(), 300);
        }
    };

    // ==========================
    // Flash Message Handler
    // ==========================
    const FlashManager = {
        addCloseButton(flashMsg) {
            if (flashMsg.querySelector('.flash-close-btn')) return;
            const closeBtn = document.createElement('span');
            closeBtn.innerHTML = '&times;';
            closeBtn.className = 'flash-close-btn';
            closeBtn.setAttribute('aria-label', 'Close');
            closeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                utils.removeFlashMessage(flashMsg);
            });
            flashMsg.style.position = 'relative';
            flashMsg.appendChild(closeBtn);
        },

        init() {
            utils.injectCloseButtonStyles();
            document.querySelectorAll('.custom-success, .custom-error').forEach(msg => this.addCloseButton(msg));
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            if (node.matches && node.matches('.custom-success, .custom-error')) {
                                this.addCloseButton(node);
                            } else if (node.querySelectorAll) {
                                node.querySelectorAll('.custom-success, .custom-error').forEach(msg => this.addCloseButton(msg));
                            }
                        }
                    });
                });
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }
    };

    // ==========================
    // Submission Guard (prevents double submissions)
    // ==========================
    const SubmissionGuard = {
        isSubmitting: false,

        /**
         * Disable submit button, show loading text
         */
        lockButton() {
            if (!DOM.submitBtn) return false;
            if (DOM.submitBtn.disabled) return false; // already locked
            DOM.submitBtn.disabled = true;
            DOM.submitBtn.textContent = 'Signing in...';
            this.isSubmitting = true;
            return true;
        },

        /**
         * Re-enable submit button (called on error or after safety timeout)
         */
        unlockButton() {
            if (!DOM.submitBtn) return;
            DOM.submitBtn.disabled = false;
            // Restore original text based on current role
            const isAdmin = DOM.userRoleInput && DOM.userRoleInput.value === 'admin';
            DOM.submitBtn.textContent = isAdmin ? 'Sign In as Admin' : 'Sign In to Counter';
            this.isSubmitting = false;
        },

        /**
         * Attach submit listener to the login form
         */
        init() {
            DOM.loginForm = utils.getElement('loginForm');
            if (!DOM.loginForm) {
                console.warn('Login form not found – submission guard not active');
                return;
            }

            DOM.loginForm.addEventListener('submit', (e) => {
                // If already submitting, block this extra submission
                if (this.isSubmitting || (DOM.submitBtn && DOM.submitBtn.disabled)) {
                    e.preventDefault();
                    return false;
                }

                // Lock the button immediately
                this.lockButton();

                // Safety net: re-enable after 10 seconds if something hangs
                setTimeout(() => {
                    if (this.isSubmitting) {
                        console.warn('Submission timeout – re‑enabling button');
                        this.unlockButton();
                    }
                }, 10000);

                // Let the form submit naturally
                return true;
            });

            // Also watch for failed submissions (flash error messages)
            // When an error appears, re-enable the button
            const observer = new MutationObserver(() => {
                if (this.isSubmitting && document.querySelector('.custom-error')) {
                    this.unlockButton();
                }
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }
    };

    // ==========================
    // UI Controller
    // ==========================
    const UIController = {
        updateOfficeID() {
            if (DOM.officeSelect && DOM.officeSelect.value) {
                DOM.officeIdDisplay.textContent = `Office ID-${DOM.officeSelect.value}`;
            } else if (DOM.officeIdDisplay) {
                DOM.officeIdDisplay.textContent = 'Office ID: Select to see ID';
            }
        },

        toggleRole(role) {
            if (!DOM.userRoleInput) return;
            DOM.userRoleInput.value = role;
            if (DOM.userInput) DOM.userInput.value = '';
            if (DOM.passwordField) DOM.passwordField.value = '';
            const isAdmin = role === 'admin';
            DOM.loginTitle.innerText = isAdmin ? 'Office Admin Login' : 'Counter Login';
            DOM.loginSubtitle.innerText = isAdmin
                ? 'Sign in to manage your office configuration'
                : 'Sign in to manage your counter\'s service queue';
            DOM.userLabel.innerText = isAdmin ? 'Administrator Email' : 'Counter Username';
            DOM.userInput.placeholder = isAdmin ? 'e.g. admin@office.gov.lk' : 'e.g. samancounter@drp';
            DOM.submitBtn.innerText = isAdmin ? 'Sign In as Admin' : 'Sign In to Counter';
            DOM.infoAlert.innerHTML = isAdmin
                ? '🔒 Passwords for Office Admins are provided by <b>My Queue Administration</b>.'
                : '🔒 Passwords for Counters are provided by your <b>Local Office Admin</b>.';
        },

        resetToCounter() {
            if (DOM.roleCounter) DOM.roleCounter.checked = true;
            if (DOM.roleAdmin) DOM.roleAdmin.checked = false;
            this.toggleRole('counter');
            if (DOM.officeSelect) DOM.officeSelect.value = '';
            if (DOM.userInput) DOM.userInput.value = '';
            if (DOM.passwordField) DOM.passwordField.value = '';
            if (DOM.officeIdDisplay) DOM.officeIdDisplay.textContent = 'Office ID: Select to see ID';
            sessionStorage.removeItem('userRole');
            sessionStorage.removeItem('userToken');
            localStorage.removeItem('rememberedRole');
            // Also reset submission guard if it was locked
            if (SubmissionGuard.isSubmitting) SubmissionGuard.unlockButton();
        },

        startStatCounters() {
            const counters = document.querySelectorAll('.stat-number');
            const speed = 200;
            counters.forEach(counter => {
                const target = parseInt(counter.getAttribute('data-target'), 10);
                if (isNaN(target)) return;
                let current = 0;
                const increment = target / speed;
                const update = () => {
                    current += increment;
                    if (current < target) {
                        counter.innerText = Math.ceil(current);
                        requestAnimationFrame(update);
                    } else {
                        counter.innerText = target;
                    }
                };
                update();
            });
        }
    };

    // ==========================
    // Data Service
    // ==========================
    const OfficeService = {
        async loadOffices() {
            try {
                const response = await fetch('/get-offices');
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const offices = await response.json();
                if (!DOM.officeSelect) return;
                DOM.officeSelect.innerHTML = '<option value="">-- Select Office --</option>';
                offices.forEach(office => {
                    const option = document.createElement('option');
                    option.value = office.id;
                    option.textContent = office.name;
                    DOM.officeSelect.appendChild(option);
                });
            } catch (error) {
                console.error('Failed to load offices:', error);
                if (DOM.officeSelect) {
                    DOM.officeSelect.innerHTML = '<option value="">Error loading offices</option>';
                }
            }
        }
    };

    // ==========================
    // Event Handlers
    // ==========================
    const EventHandlers = {
        onRoleChange(e) {
            const target = e.target;
            if (target.id === 'roleCounter' && target.checked) {
                UIController.toggleRole('counter');
            } else if (target.id === 'roleAdmin' && target.checked) {
                UIController.toggleRole('admin');
            }
        },

        onOfficeChange() {
            UIController.updateOfficeID();
        },

        onPageShow(event) {
            if (event.persisted || (performance.getEntriesByType('navigation')[0]?.type === 'back_forward')) {
                UIController.resetToCounter();
            }
        },

        onPopState() {
            UIController.resetToCounter();
        }
    };

    // ==========================
    // Initialization
    // ==========================
    async function init() {
        // Cache DOM elements
        DOM.officeSelect = utils.getElement('officeSelect');
        DOM.officeIdDisplay = utils.getElement('officeIdDisplay');
        DOM.roleCounter = utils.getElement('roleCounter');
        DOM.roleAdmin = utils.getElement('roleAdmin');
        DOM.userRoleInput = utils.getElement('userRoleInput');
        DOM.userInput = utils.getElement('userInput');
        DOM.passwordField = utils.getElement('passwordField');
        DOM.loginTitle = utils.getElement('loginTitle');
        DOM.loginSubtitle = utils.getElement('loginSubtitle');
        DOM.submitBtn = utils.getElement('submitBtn');
        DOM.userLabel = utils.getElement('userLabel');
        DOM.infoAlert = utils.getElement('infoAlert');

        await OfficeService.loadOffices();
        UIController.resetToCounter();
        FlashManager.init();

        const hasLogout = Array.from(document.querySelectorAll('.custom-success, .custom-error')).some(
            msg => msg.textContent.includes('Logged out successfully')
        );
        if (hasLogout) UIController.resetToCounter();

        UIController.startStatCounters();

        // Set up event listeners
        if (DOM.roleCounter && DOM.roleAdmin) {
            document.querySelector('.role-selector')?.addEventListener('change', EventHandlers.onRoleChange);
        }
        if (DOM.officeSelect) {
            DOM.officeSelect.addEventListener('change', EventHandlers.onOfficeChange);
        }

        window.addEventListener('pageshow', EventHandlers.onPageShow);
        window.addEventListener('popstate', EventHandlers.onPopState);

        // ✅ Initialize submission guard (prevents double submission)
        SubmissionGuard.init();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();