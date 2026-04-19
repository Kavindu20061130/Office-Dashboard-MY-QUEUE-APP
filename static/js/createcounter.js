/* ═══════════════════════════════════════════════
   createcounter.js — QueueLK Admin (INLINE FORM)
═══════════════════════════════════════════════ */

// ── Toast ──────────────────────────────────────
function toast(msg, type = 'success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast show ${type}`;
  setTimeout(() => t.classList.remove('show'), 3300);
}

// ── Dashboard Navigation ─────────────────────────
function goBackToDashboard() {
  const successPopup = document.getElementById('successPopup');
  const deletePopup = document.getElementById('deleteConfirmPopup');
  if (successPopup) successPopup.classList.remove('active');
  if (deletePopup) deletePopup.classList.remove('active');
  window.location.href = '/dashboard';
}

// ── Step flow: Landing → Inline Form ─────────────────
let currentMode = 'new';

function selectMode(mode) {
  currentMode = mode;
  
  // Hide the entire landing card content except the form trigger? Actually hide the badge and title
  const landingBadge = document.querySelector('.landing-badge');
  const landingTitle = document.querySelector('.landing-title');
  const choiceContainer = document.querySelector('.choice-container');
  
  if (landingBadge) landingBadge.style.display = 'none';
  if (landingTitle) landingTitle.style.display = 'none';
  if (choiceContainer) choiceContainer.style.display = 'none';
  
  // Show the form inline
  const backdrop = document.getElementById('modalBackdrop');
  backdrop.classList.remove('hidden');
  backdrop.classList.add('visible');
  
  // Switch to selected tab
  switchTab(mode);
}

// ── Tab switch with animated slider ────
function switchTab(mode) {
  currentMode = mode;

  const tabNew = document.querySelector('.tab[data-tab="new"]');
  const tabExisting = document.querySelector('.tab[data-tab="existing"]');
  const slider = document.getElementById('tabSlider');

  if (!tabNew || !tabExisting) {
    console.error('Tab buttons not found');
    return;
  }

  // Update tab active states
  if (mode === 'new') {
    tabNew.classList.add('active');
    tabExisting.classList.remove('active');
    document.getElementById('newCard').style.display = 'flex';
    document.getElementById('existingCard').style.display = 'none';
    resetUsernameCheck();
  } else {
    tabNew.classList.remove('active');
    tabExisting.classList.add('active');
    document.getElementById('newCard').style.display = 'none';
    document.getElementById('existingCard').style.display = 'flex';
    
    // Reset staff selection when switching to manage tab
    const staffSelect = document.getElementById('staffSelect');
    if (staffSelect) staffSelect.value = '';
    const editPanel = document.getElementById('editPanel');
    if (editPanel) editPanel.style.display = 'none';
  }

  // Animate slider
  requestAnimationFrame(() => {
    const activeTab = mode === 'new' ? tabNew : tabExisting;
    const bar = document.querySelector('.tab-bar');
    if (activeTab && bar && slider) {
      const barRect = bar.getBoundingClientRect();
      const tabRect = activeTab.getBoundingClientRect();
      slider.style.left = (tabRect.left - barRect.left) + 'px';
      slider.style.width = tabRect.width + 'px';
    }
  });
}

// ── SUCCESS POPUP FUNCTIONS ────────────────────
function showSuccessPopup(staffData) {
  const successUsername = document.getElementById('successUsername');
  const successCounter = document.getElementById('successCounter');
  const popup = document.getElementById('successPopup');
  
  if (successUsername) successUsername.textContent = staffData.username;
  if (successCounter) successCounter.textContent = staffData.counter;
  if (popup) popup.classList.add('active');
}

function hideSuccessPopup() {
  const popup = document.getElementById('successPopup');
  if (popup) popup.classList.remove('active');
}

function goToDashboardFromPopup() {
  window.location.href = '/dashboard';
}

function addAnotherStaff() {
  hideSuccessPopup();
  
  // Reset new staff form
  const newUsername = document.getElementById('newUsername');
  const newPassword = document.getElementById('newPassword');
  const newConfirm = document.getElementById('newConfirm');
  const newCounterName = document.getElementById('newCounterName');
  const tipCheck = document.getElementById('tipCheck');
  const usernameMsg = document.getElementById('usernameAvailabilityMsg');
  const strengthMsg = document.getElementById('newStrengthMsg');
  const matchMsg = document.getElementById('newMatchMsg');
  
  if (newUsername) newUsername.value = '';
  if (newPassword) newPassword.value = '';
  if (newConfirm) newConfirm.value = '';
  if (newCounterName) newCounterName.value = '';
  if (tipCheck) tipCheck.checked = false;
  if (usernameMsg) usernameMsg.innerHTML = '';
  if (strengthMsg) strengthMsg.innerHTML = '';
  if (matchMsg) matchMsg.innerHTML = '';
  
  const existingRadio = document.querySelector('input[name="counterOption"][value="existing"]');
  if (existingRadio) existingRadio.checked = true;
  toggleCounterInputs('new');
  
  isUsernameAvailable = false;
  isUsernameLengthValid = false;
  updateCreateButtonState();
  
  if (newUsername) newUsername.focus();
  
  // Ensure form is visible
  const backdrop = document.getElementById('modalBackdrop');
  if (backdrop && !backdrop.classList.contains('visible')) {
    backdrop.classList.add('visible');
  }
  switchTab('new');
}

// ── Username availability ──────────────────────
let usernameCheckTimeout = null;
let isUsernameAvailable = false;
let isUsernameLengthValid = false;

function resetUsernameCheck() {
  const msgDiv = document.getElementById('usernameAvailabilityMsg');
  const usernameInput = document.getElementById('newUsername');
  
  if (msgDiv) msgDiv.innerHTML = '';
  if (usernameInput) usernameInput.value = '';
  
  isUsernameAvailable = false;
  isUsernameLengthValid = false;
  updateCreateButtonState();
}

function checkUsernameAvailability() {
  const username = document.getElementById('newUsername').value.trim();
  const msgDiv = document.getElementById('usernameAvailabilityMsg');
  
  if (!username) {
    msgDiv.innerHTML = '';
    isUsernameAvailable = false;
    isUsernameLengthValid = false;
    updateCreateButtonState();
    return;
  }
  
  if (username.length < 8) {
    msgDiv.innerHTML = '<span class="invalid-length">❌ Username must be at least 8 characters</span>';
    isUsernameLengthValid = false;
    isUsernameAvailable = false;
    updateCreateButtonState();
    return;
  }
  
  isUsernameLengthValid = true;
  msgDiv.innerHTML = '<span style="color:rgba(237,250,243,.45)">⏳ Checking availability...</span>';
  
  fetch(`/check-username?username=${encodeURIComponent(username)}`)
    .then(response => response.json())
    .then(data => {
      const isAvailable = data.available === true || data.exists === false || data.success === true;
      
      if (isAvailable) {
        msgDiv.innerHTML = '<span class="username-available">✅ Username available</span>';
        isUsernameAvailable = true;
      } else {
        msgDiv.innerHTML = '<span class="username-taken">❌ Username already taken</span>';
        isUsernameAvailable = false;
      }
      updateCreateButtonState();
    })
    .catch(error => {
      console.error('Network error:', error);
      msgDiv.innerHTML = '<span class="weak">⚠️ Network error - please try again</span>';
      isUsernameAvailable = false;
      updateCreateButtonState();
    });
}

function onUsernameInput() {
  clearTimeout(usernameCheckTimeout);
  usernameCheckTimeout = setTimeout(checkUsernameAvailability, 500);
}

// ── Create button state ────────────────────────
function isPasswordValid(pwd) {
  return pwd.length >= 8 && pwd.length <= 18 && /\d/.test(pwd);
}

function updateCreateButtonState() {
  const tipOk = document.getElementById('tipCheck')?.checked || false;
  const opt = document.querySelector('input[name="counterOption"]:checked')?.value;
  const ctrOk = opt === 'existing'
    ? !!document.getElementById('newExistingCounter')?.value
    : (document.getElementById('newCounterName')?.value.trim() !== '');
  const pwOk = isPasswordValid(document.getElementById('newPassword')?.value || '');
  const matchOk = document.getElementById('newPassword')?.value === document.getElementById('newConfirm')?.value;
  const btn = document.getElementById('createBtn');
  
  if (btn) btn.disabled = !(isUsernameAvailable && isUsernameLengthValid && tipOk && ctrOk && pwOk && matchOk);
}

// ── Password strength/match NEW ────────────────
function checkNewPasswordStrength() {
  const pwd = document.getElementById('newPassword')?.value || '';
  const div = document.getElementById('newStrengthMsg');
  if (!pwd) { if(div) div.innerHTML = ''; updateCreateButtonState(); return; }
  if (pwd.length >= 8 && pwd.length <= 18 && /\d/.test(pwd))
    div.innerHTML = '<span class="strong">✅ Strong</span>';
  else if (pwd.length < 8)
    div.innerHTML = '<span class="weak">❌ Too short</span>';
  else if (pwd.length > 18)
    div.innerHTML = '<span class="weak">❌ Too long</span>';
  else
    div.innerHTML = '<span class="medium">⚠️ Need a digit</span>';
  updateCreateButtonState();
}

function checkNewPasswordMatch() {
  const pwd = document.getElementById('newPassword')?.value || '';
  const conf = document.getElementById('newConfirm')?.value || '';
  const div = document.getElementById('newMatchMsg');
  if (!conf) { if(div) div.innerHTML = ''; updateCreateButtonState(); return; }
  div.innerHTML = (pwd === conf && pwd)
    ? '<span class="match-ok">✅ Match</span>'
    : '<span class="match-bad">❌ No match</span>';
  updateCreateButtonState();
}

// ── Counter input toggle ───────────────────────
function toggleCounterInputs(ctx) {
  if (ctx === 'new') {
    const isEx = document.querySelector('input[name="counterOption"]:checked')?.value === 'existing';
    const existingDiv = document.getElementById('newExistingCounterDiv');
    const newDiv = document.getElementById('newNewCounterDiv');
    if (existingDiv) existingDiv.style.display = isEx ? 'block' : 'none';
    if (newDiv) newDiv.style.display = isEx ? 'none' : 'block';
    updateCreateButtonState();
  } else {
    const isEx = document.querySelector('input[name="editCounterOption"]:checked')?.value === 'existing';
    const existingDiv = document.getElementById('editExistingCounterDiv');
    const newDiv = document.getElementById('editNewCounterDiv');
    if (existingDiv) existingDiv.style.display = isEx ? 'block' : 'none';
    if (newDiv) newDiv.style.display = isEx ? 'none' : 'block';
    const rb = document.getElementById('renameCounterBlock');
    if (rb) rb.style.display = isEx ? 'block' : 'none';
  }
}

// ── Create staff (WITH SUCCESS POPUP) ──────────
function createStaff() {
  const username = document.getElementById('newUsername')?.value.trim() || '';
  const password = document.getElementById('newPassword')?.value || '';
  const confirm = document.getElementById('newConfirm')?.value || '';
  const queueId = document.getElementById('queueSelect')?.value || '';
  const tipChecked = document.getElementById('tipCheck')?.checked || false;

  if (!username || username.length < 8) { toast('Username must be at least 8 chars', 'error'); return; }
  if (!isUsernameAvailable) { toast('Username not available', 'error'); return; }
  if (!isPasswordValid(password)) { toast('Password must be 8–18 chars with a digit', 'error'); return; }
  if (password !== confirm) { toast('Passwords do not match', 'error'); return; }
  if (!tipChecked) { toast('Please confirm the details first', 'error'); return; }

  const opt = document.querySelector('input[name="counterOption"]:checked')?.value;
  let existingCounterId = null, newCounterName = null;
  let counterDisplayName = '';
  
  if (opt === 'existing') {
    existingCounterId = document.getElementById('newExistingCounter')?.value;
    if (!existingCounterId) { toast('Select an existing counter', 'error'); return; }
    const select = document.getElementById('newExistingCounter');
    counterDisplayName = select.options[select.selectedIndex]?.text.split(' (')[0] || 'Selected Counter';
  } else {
    newCounterName = document.getElementById('newCounterName')?.value.trim() || '';
    if (!newCounterName) { toast('Enter a name for the new counter', 'error'); return; }
    counterDisplayName = newCounterName;
  }

  const createBtn = document.getElementById('createBtn');
  const originalBtnText = createBtn?.innerHTML || 'Create Staff Account';
  
  if (createBtn) {
    createBtn.innerHTML = '<span class="loading-spinner"></span> Creating...';
    createBtn.disabled = true;
  }

  const body = new URLSearchParams({ username, password, confirm_password: confirm, queue_id: queueId });
  if (existingCounterId) body.append('existing_counter_id', existingCounterId);
  else body.append('counter_name', newCounterName);

  fetch('/create-staff', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body
  })
  .then(r => r.json())
  .then(d => {
    if (createBtn) {
      createBtn.innerHTML = originalBtnText;
      createBtn.disabled = false;
    }
    
    if (d.success) {
      showSuccessPopup({
        username: username,
        counter: counterDisplayName,
        status: 'Active'
      });
      
      // Reset form
      const newUsername = document.getElementById('newUsername');
      const newPassword = document.getElementById('newPassword');
      const newConfirm = document.getElementById('newConfirm');
      const newCounterName = document.getElementById('newCounterName');
      const tipCheck = document.getElementById('tipCheck');
      const usernameMsg = document.getElementById('usernameAvailabilityMsg');
      const strengthMsg = document.getElementById('newStrengthMsg');
      const matchMsg = document.getElementById('newMatchMsg');
      
      if (newUsername) newUsername.value = '';
      if (newPassword) newPassword.value = '';
      if (newConfirm) newConfirm.value = '';
      if (newCounterName) newCounterName.value = '';
      if (tipCheck) tipCheck.checked = false;
      if (usernameMsg) usernameMsg.innerHTML = '';
      if (strengthMsg) strengthMsg.innerHTML = '';
      if (matchMsg) matchMsg.innerHTML = '';
      
      const existingRadio = document.querySelector('input[name="counterOption"][value="existing"]');
      if (existingRadio) existingRadio.checked = true;
      toggleCounterInputs('new');
      
      isUsernameAvailable = false;
      isUsernameLengthValid = false;
      updateCreateButtonState();
    } else {
      toast(d.error || 'Creation failed', 'error');
    }
  })
  .catch(() => {
    if (createBtn) {
      createBtn.innerHTML = originalBtnText;
      createBtn.disabled = false;
    }
    toast('Network error', 'error');
  });
}

// ── Load staff for edit ────────────────────────
function loadStaffDetails() {
  const select = document.getElementById('staffSelect');
  if (!select || !select.value) { 
    const editPanel = document.getElementById('editPanel');
    if (editPanel) editPanel.style.display = 'none';
    return; 
  }
  
  const opt = select.options[select.selectedIndex];
  const editUsernameLabel = document.getElementById('editUsernameLabel');
  const editStatus = document.getElementById('editStatus');
  const editCounterName = document.getElementById('editCounterName');
  const editQueueSelect = document.getElementById('editQueueSelect');
  const editPanel = document.getElementById('editPanel');
  
  if (editUsernameLabel) editUsernameLabel.innerText = opt.getAttribute('data-username') || '';
  if (editStatus) editStatus.value = opt.getAttribute('data-status') || 'active';

  const counterId = opt.getAttribute('data-counter');
  const queueId = opt.getAttribute('data-queue');

  const exSel = document.getElementById('editExistingCounter');
  if (exSel) {
    for (const o of exSel.options) {
      if (o.value === counterId) { 
        o.selected = true; 
        break; 
      }
    }
    if (editCounterName) {
      editCounterName.value = exSel.options[exSel.selectedIndex]?.getAttribute('data-name') || '';
    }
  }

  if (editQueueSelect) editQueueSelect.value = queueId || '';

  const editPassword = document.getElementById('editPassword');
  const editConfirm = document.getElementById('editConfirm');
  const editStrengthMsg = document.getElementById('editStrengthMsg');
  const editMatchMsg = document.getElementById('editMatchMsg');
  
  if (editPassword) editPassword.value = '';
  if (editConfirm) editConfirm.value = '';
  if (editStrengthMsg) editStrengthMsg.innerHTML = '';
  if (editMatchMsg) editMatchMsg.innerHTML = '';
  
  if (editPanel) {
    editPanel.setAttribute('data-staff-id', select.value);
    editPanel.style.display = 'block';
  }
  
  const existingRadio = document.querySelector('input[name="editCounterOption"][value="existing"]');
  if (existingRadio) existingRadio.checked = true;
  toggleCounterInputs('edit');
}

// ── Rename counter ─────────────────────────────
function renameCounter() {
  const ctrSel = document.getElementById('editExistingCounter');
  if (!ctrSel) return;
  const ctrId = ctrSel.value;
  if (!ctrId) { toast('No counter selected', 'error'); return; }
  const newName = document.getElementById('editCounterName')?.value.trim();
  if (!newName) { toast('Counter name required', 'error'); return; }
  
  fetch(`/update-counter/${ctrId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ name: newName })
  })
  .then(r => r.json())
  .then(d => {
    if (d.success) {
      toast('Counter renamed ✓');
      const o = ctrSel.options[ctrSel.selectedIndex];
      if (o) {
        o.setAttribute('data-name', newName);
        o.textContent = newName;
      }
    } else {
      toast(d.error || 'Rename failed', 'error');
    }
  })
  .catch(() => toast('Network error', 'error'));
}

// ── Save staff changes ─────────────────────────
function saveStaffChanges() {
  const editPanel = document.getElementById('editPanel');
  if (!editPanel) return;
  const staffId = editPanel.getAttribute('data-staff-id');
  if (!staffId) return;
  
  const status = document.getElementById('editStatus')?.value || 'active';
  const password = document.getElementById('editPassword')?.value || '';
  const confirm = document.getElementById('editConfirm')?.value || '';
  const queueId = document.getElementById('editQueueSelect')?.value || '';

  if (password) {
    if (password !== confirm) { toast('Passwords do not match', 'error'); return; }
    if (!isPasswordValid(password)) { toast('Password 8–18 chars with a digit', 'error'); return; }
  }

  const opt = document.querySelector('input[name="editCounterOption"]:checked')?.value;
  let existingCounterId = null, newCounterName = null;
  if (opt === 'existing') {
    existingCounterId = document.getElementById('editExistingCounter')?.value;
    if (!existingCounterId) { toast('Select an existing counter', 'error'); return; }
  } else {
    newCounterName = document.getElementById('editNewCounterName')?.value.trim() || '';
    if (!newCounterName) { toast('Enter a name for the new counter', 'error'); return; }
  }

  const formData = new URLSearchParams({ status, queue_id: queueId });
  if (password) { formData.append('password', password); formData.append('confirm_password', confirm); }
  if (existingCounterId) formData.append('existing_counter_id', existingCounterId);
  else formData.append('new_counter_name', newCounterName);

  fetch(`/update-staff/${staffId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData
  })
  .then(r => r.json())
  .then(d => {
    if (d.success) { toast('Staff updated ✓', 'success'); setTimeout(() => location.reload(), 1000); }
    else toast(d.error || 'Update failed', 'error');
  })
  .catch(() => toast('Network error', 'error'));
}

// ── Delete staff (WITH CUSTOM MODAL) ───────────
let pendingDeleteStaffId = null;

function showDeleteConfirm(staffId, staffName, staffStatus, staffCounter) {
  pendingDeleteStaffId = staffId;
  const deleteStaffNameSpan = document.getElementById('deleteStaffName');
  const deleteStaffStatusSpan = document.getElementById('deleteStaffStatus');
  const deleteStaffCounterSpan = document.getElementById('deleteStaffCounter');
  
  if (deleteStaffNameSpan) deleteStaffNameSpan.textContent = staffName;
  if (deleteStaffStatusSpan) deleteStaffStatusSpan.textContent = staffStatus || 'Active';
  if (deleteStaffCounterSpan) deleteStaffCounterSpan.textContent = staffCounter || 'Not assigned';
  
  const popup = document.getElementById('deleteConfirmPopup');
  if (popup) popup.classList.add('active');
}

function hideDeleteConfirm() {
  const popup = document.getElementById('deleteConfirmPopup');
  if (popup) popup.classList.remove('active');
  pendingDeleteStaffId = null;
}

function executeDeleteStaff() {
  if (!pendingDeleteStaffId) return;
  
  fetch(`/delete-staff/${pendingDeleteStaffId}`, { method: 'POST' })
    .then(r => r.json())
    .then(d => {
      if (d.success) { 
        toast('Staff deleted successfully', 'success'); 
        setTimeout(() => location.reload(), 1000);
      } else {
        toast(d.error, 'error');
      }
      hideDeleteConfirm();
    })
    .catch(() => {
      toast('Network error', 'error');
      hideDeleteConfirm();
    });
}

function deleteStaff() {
  const editPanel = document.getElementById('editPanel');
  if (!editPanel) return;
  const staffId = editPanel.getAttribute('data-staff-id');
  if (!staffId) return;
  
  const select = document.getElementById('staffSelect');
  if (!select) return;
  const selectedOption = select.options[select.selectedIndex];
  const staffName = selectedOption?.getAttribute('data-username') || 'Unknown';
  const staffStatus = document.getElementById('editStatus')?.value || 'Active';
  
  const counterSelect = document.getElementById('editExistingCounter');
  let staffCounter = 'Not assigned';
  if (counterSelect && counterSelect.value) {
    staffCounter = counterSelect.options[counterSelect.selectedIndex]?.text || 'Selected counter';
  }
  
  showDeleteConfirm(staffId, staffName, staffStatus, staffCounter);
}

// ── Edit password strength/match ───────────────
function checkEditPasswordStrength() {
  const pwd = document.getElementById('editPassword')?.value || '';
  const div = document.getElementById('editStrengthMsg');
  if (!pwd) { if(div) div.innerHTML = ''; return; }
  if (pwd.length >= 8 && pwd.length <= 18 && /\d/.test(pwd))
    div.innerHTML = '<span class="strong">✅ Valid</span>';
  else if (pwd.length < 8) div.innerHTML = '<span class="weak">❌ Min 8</span>';
  else if (pwd.length > 18) div.innerHTML = '<span class="weak">❌ Max 18</span>';
  else div.innerHTML = '<span class="medium">⚠️ Need a digit</span>';
}

function checkEditPasswordMatch() {
  const pwd = document.getElementById('editPassword')?.value || '';
  const conf = document.getElementById('editConfirm')?.value || '';
  const div = document.getElementById('editMatchMsg');
  if (!conf) { if(div) div.innerHTML = ''; return; }
  div.innerHTML = (pwd === conf)
    ? '<span class="match-ok">✅ Match</span>'
    : '<span class="match-bad">❌ Mismatch</span>';
}

// ── DOM ready ──────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Initially hide the form
  const backdrop = document.getElementById('modalBackdrop');
  if (backdrop) {
    backdrop.classList.add('hidden');
  }
  
  // Set up tab click handlers
  const tabNew = document.querySelector('.tab[data-tab="new"]');
  const tabExisting = document.querySelector('.tab[data-tab="existing"]');
  
  if (tabNew) {
    tabNew.addEventListener('click', () => switchTab('new'));
  }
  if (tabExisting) {
    tabExisting.addEventListener('click', () => switchTab('existing'));
  }
  
  switchTab('new');

  const newUsername = document.getElementById('newUsername');
  if (newUsername) newUsername.addEventListener('input', onUsernameInput);
  
  const tipCheck = document.getElementById('tipCheck');
  if (tipCheck) tipCheck.addEventListener('change', updateCreateButtonState);
  
  const newExistingCounter = document.getElementById('newExistingCounter');
  if (newExistingCounter) newExistingCounter.addEventListener('change', updateCreateButtonState);
  
  const newCounterName = document.getElementById('newCounterName');
  if (newCounterName) newCounterName.addEventListener('input', updateCreateButtonState);
  
  document.querySelectorAll('input[name="counterOption"]').forEach(r =>
    r.addEventListener('change', () => { toggleCounterInputs('new'); updateCreateButtonState(); })
  );
  
  const newPassword = document.getElementById('newPassword');
  if (newPassword) {
    newPassword.addEventListener('input', () => {
      checkNewPasswordStrength(); 
      checkNewPasswordMatch();
    });
  }
  
  const newConfirm = document.getElementById('newConfirm');
  if (newConfirm) newConfirm.addEventListener('input', checkNewPasswordMatch);
  
  const createBtn = document.getElementById('createBtn');
  if (createBtn) createBtn.addEventListener('click', createStaff);
  
  const skipQueueBtn = document.getElementById('skipQueueBtn');
  if (skipQueueBtn) {
    skipQueueBtn.addEventListener('click', () => {
      const queueSelect = document.getElementById('queueSelect');
      if (queueSelect) queueSelect.value = '';
    });
  }

  const staffSelect = document.getElementById('staffSelect');
  if (staffSelect) staffSelect.addEventListener('change', loadStaffDetails);
  
  const editPassword = document.getElementById('editPassword');
  if (editPassword) {
    editPassword.addEventListener('input', () => {
      checkEditPasswordStrength(); 
      checkEditPasswordMatch();
    });
  }
  
  const editConfirm = document.getElementById('editConfirm');
  if (editConfirm) editConfirm.addEventListener('input', checkEditPasswordMatch);
  
  const saveStaffBtn = document.getElementById('saveStaffBtn');
  if (saveStaffBtn) saveStaffBtn.addEventListener('click', saveStaffChanges);
  
  const deleteStaffBtn = document.getElementById('deleteStaffBtn');
  if (deleteStaffBtn) deleteStaffBtn.addEventListener('click', deleteStaff);
  
  const renameCounterBtn = document.getElementById('renameCounterBtn');
  if (renameCounterBtn) renameCounterBtn.addEventListener('click', renameCounter);
  
  const unassignQueueBtn = document.getElementById('unassignQueueBtn');
  if (unassignQueueBtn) {
    unassignQueueBtn.addEventListener('click', () => {
      const editQueueSelect = document.getElementById('editQueueSelect');
      if (editQueueSelect) editQueueSelect.value = '';
    });
  }
  
  document.querySelectorAll('input[name="editCounterOption"]').forEach(r =>
    r.addEventListener('change', () => toggleCounterInputs('edit'))
  );
  
  const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
  if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', executeDeleteStaff);
  
  const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
  if (cancelDeleteBtn) cancelDeleteBtn.addEventListener('click', hideDeleteConfirm);
  
  const deleteConfirmPopup = document.getElementById('deleteConfirmPopup');
  if (deleteConfirmPopup) {
    deleteConfirmPopup.addEventListener('click', function(e) {
      if (e.target === this) hideDeleteConfirm();
    });
  }
  
  const addAnotherBtn = document.getElementById('addAnotherBtn');
  if (addAnotherBtn) addAnotherBtn.addEventListener('click', addAnotherStaff);
  
  const goDashboardBtn = document.getElementById('goDashboardBtn');
  if (goDashboardBtn) goDashboardBtn.addEventListener('click', goToDashboardFromPopup);
  
  const successPopup = document.getElementById('successPopup');
  if (successPopup) {
    successPopup.addEventListener('click', function(e) {
      if (e.target === this) hideSuccessPopup();
    });
  }

  updateCreateButtonState();
});