/* ═══════════════════════════════════════════════
   createqueue.js — Queue & Service Management
═══════════════════════════════════════════════ */

/* ══════════════════════════════════════════
   LANDING SCENE → selectMode()
══════════════════════════════════════════ */
function selectMode(mode) {
  const scene    = document.getElementById('landingScene');
  const backdrop = document.getElementById('modalBackdrop');

  // Animate scene out
  if (scene) scene.classList.add('out');

  // After scene fades, show the card
  setTimeout(() => {
    if (scene)    scene.style.display = 'none';
    if (backdrop) {
      backdrop.classList.remove('hidden');
      backdrop.classList.add('visible');
    }
    // Switch to the correct tab
    switchTab(mode);
  }, 420);
}

/* If coming back from a success redirect (success_data present),
   skip the landing and go straight to the queue card */
function checkAutoOpen() {
  const el = document.getElementById('successData');
  if (el && el.dataset.queueName) {
    const scene    = document.getElementById('landingScene');
    const backdrop = document.getElementById('modalBackdrop');
    if (scene)    scene.style.display = 'none';
    if (backdrop) { backdrop.classList.remove('hidden'); backdrop.classList.add('visible'); }
    switchTab('queue');
  }
}

/* ─── Tab switching ─── */
function switchTab(mode) {
  document.querySelectorAll('.tab').forEach(t =>
    t.classList.toggle('active', t.dataset.tab === mode)
  );

  const tabSlider = document.getElementById('tabSlider');
  const activeTab = document.querySelector(`.tab[data-tab="${mode}"]`);
  if (activeTab && tabSlider) {
    tabSlider.style.left  = activeTab.offsetLeft + 'px';
    tabSlider.style.width = activeTab.offsetWidth + 'px';
  }

  const queueCard   = document.getElementById('queueCard');
  const serviceCard = document.getElementById('serviceCard');
  if (queueCard)   queueCard.style.display   = mode === 'queue'   ? 'flex' : 'none';
  if (serviceCard) serviceCard.style.display = mode === 'service' ? 'flex' : 'none';
}

function initTabs() {
  const tabSlider = document.getElementById('tabSlider');
  const firstActive = document.querySelector('.tab.active');
  if (firstActive && tabSlider) {
    tabSlider.style.left  = firstActive.offsetLeft + 'px';
    tabSlider.style.width = firstActive.offsetWidth + 'px';
  }
  document.querySelectorAll('.tab').forEach(btn =>
    btn.addEventListener('click', () => switchTab(btn.dataset.tab))
  );
}

/* ─── Toast ─── */
function showToast(msg, type = 'info') {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.className   = 'toast ' + type;
  void el.offsetWidth;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 3400);
}

/* ─── Service option toggle (queue form) ─── */
function initServiceToggle() {
  const radios   = document.querySelectorAll('input[name="service_option"]');
  const existing = document.getElementById('existingServiceDiv');
  const custom   = document.getElementById('customServiceDiv');
  if (!radios.length) return;

  function toggle() {
    const val = document.querySelector('input[name="service_option"]:checked')?.value;
    if (existing) existing.style.display = val === 'existing' ? 'block' : 'none';
    if (custom)   custom.style.display   = val === 'custom'   ? 'block' : 'none';
  }
  radios.forEach(r => r.addEventListener('change', toggle));
  toggle();
}

/* ─── Token preview ─── */
function initTokenPreview() {
  const letter   = document.getElementById('token_letter');
  const startNum = document.getElementById('token_start_number');
  const maxCap   = document.getElementById('max_capacity');
  const preview  = document.getElementById('tokenPreview');
  if (!letter || !preview) return;

  const pad = n => n.toString().padStart(3, '0');
  function update() {
    const L = letter.value || 'A';
    const S = parseInt(startNum.value, 10) || 1;
    const M = Math.max(1, parseInt(maxCap.value, 10) || 50);
    preview.textContent = L + '-' + pad(S) + '  \u2192  ' + L + '-' + pad(S + M - 1);
  }
  letter.addEventListener('change', update);
  startNum.addEventListener('input', update);
  maxCap.addEventListener('input', update);
  update();
}

/* ─── Loading overlay ─── */
function showLoading() {
  const ol = document.getElementById('loadingOverlay');
  if (ol) ol.style.display = 'flex';
}
function hideLoading() {
  const ol = document.getElementById('loadingOverlay');
  if (ol) ol.style.display = 'none';
}

/* ══════════════════════════════════════════
   QUEUE SUCCESS POPUP
══════════════════════════════════════════ */
function showQueueSuccessPopup(data) {
  hideLoading();
  const overlay = document.getElementById('successOverlay');
  if (!overlay) return;
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  set('popupQueueName',    data.queueName    || '\u2014');
  set('popupQueueIds',     data.queueIds     || '\u2014');
  set('popupCounterCount', data.counterCount || '\u2014');
  set('popupCreatedAt',    new Date().toLocaleString());
  overlay.classList.add('active');
  const flashes = document.querySelector('.flash-messages');
  if (flashes) flashes.style.display = 'none';
}

function closeQueueSuccessPopup() {
  document.getElementById('successOverlay')?.classList.remove('active');
}

/* ══════════════════════════════════════════
   SERVICE SUCCESS POPUP
══════════════════════════════════════════ */
function showServiceSuccessPopup(data) {
  const overlay = document.getElementById('serviceSuccessOverlay');
  if (!overlay) return;
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  set('svcPopupId',     data.service_id || '\u2014');
  set('svcPopupName',   data.name       || '\u2014');
  set('svcPopupCharge', 'LKR ' + (data.charge || 0).toLocaleString());
  set('svcPopupAt',     new Date().toLocaleString());
  overlay.classList.add('active');
}

function closeServiceSuccessPopup() {
  document.getElementById('serviceSuccessOverlay')?.classList.remove('active');
}

/* ══════════════════════════════════════════
   SERVICE FORM — AJAX SUBMIT
══════════════════════════════════════════ */
function initServiceForm() {
  const form      = document.getElementById('serviceForm');
  const submitBtn = document.getElementById('svcSubmitBtn');
  if (!form || !submitBtn) return;

  form.addEventListener('submit', async function(e) {
    e.preventDefault();

    const nameInput   = document.getElementById('svcName');
    const chargeInput = document.getElementById('svcCharge');
    const name        = (nameInput?.value   || '').trim();
    const charge      = (chargeInput?.value || '').trim();

    if (!name) {
      showToast('Service name is required', 'error');
      nameInput?.focus();
      return;
    }
    if (!charge || isNaN(Number(charge)) || Number(charge) < 0) {
      showToast('Enter a valid charge amount', 'error');
      chargeInput?.focus();
      return;
    }

    const origHTML      = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span class="loading-spinner"></span>&nbsp;Creating\u2026';
    submitBtn.disabled  = true;

    try {
      const res  = await fetch('/create-service', {
        method:  'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body:    new URLSearchParams({ service_name: name, service_charge: charge })
      });
      const data = await res.json();

      if (data.success) {
        if (nameInput)   nameInput.value   = '';
        if (chargeInput) chargeInput.value = '';
        showServiceSuccessPopup(data);
      } else {
        showToast(data.error || 'Failed to create service', 'error');
      }
    } catch (err) {
      showToast('Network error \u2014 please try again', 'error');
    } finally {
      submitBtn.innerHTML = origHTML;
      submitBtn.disabled  = false;
    }
  });
}

/* ─── Server-injected queue success data ─── */
function checkSuccessData() {
  const el = document.getElementById('successData');
  if (!el) return;
  const { queueName, queueIds, counterCount } = el.dataset;
  if (queueName && queueIds && counterCount) {
    showQueueSuccessPopup({ queueName, queueIds, counterCount });
  }
}

/* ─── Flash message auto-hide ─── */
function initFlashMessages() {
  document.querySelectorAll('.flash-msg').forEach(f => {
    f.addEventListener('click', () => f.remove());
  });
  setTimeout(() => {
    document.querySelectorAll('.flash-msg').forEach(f => {
      f.style.transition = 'opacity .5s';
      f.style.opacity    = '0';
      setTimeout(() => f.remove(), 500);
    });
  }, 5000);
}

/* ─── Init ─── */
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initServiceToggle();
  initTokenPreview();
  initFlashMessages();
  checkSuccessData();
  checkAutoOpen();
  initServiceForm();

  document.getElementById('addAnotherBtn')
    ?.addEventListener('click', closeQueueSuccessPopup);

  document.getElementById('svcAddAnotherBtn')
    ?.addEventListener('click', closeServiceSuccessPopup);

  ['successOverlay', 'serviceSuccessOverlay'].forEach(id => {
    document.getElementById(id)?.addEventListener('click', function(e) {
      if (e.target === this) this.classList.remove('active');
    });
  });

  document.getElementById('queueForm')
    ?.addEventListener('submit', () => showLoading());
});