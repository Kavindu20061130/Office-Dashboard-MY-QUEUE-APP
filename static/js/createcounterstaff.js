<script>
  // Toast helper
  function toast(msg, type='success') {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = `toast show ${type}`;
    setTimeout(() => t.classList.remove('show'), 3300);
  }

  function toggleMode() {
    const mode = document.getElementById('modeSelect').value;
    document.getElementById('newCard').style.display = mode === 'new' ? 'block' : 'none';
    document.getElementById('existingCard').style.display = mode === 'existing' ? 'block' : 'none';
    if (mode === 'existing') {
      document.getElementById('staffSelect').value = '';
      document.getElementById('editPanel').style.display = 'none';
    }
  }

  // ----- Username availability (global, min 8 chars) -----
  let usernameCheckTimeout = null;
  let isUsernameAvailable = false;
  let isUsernameLengthValid = false;

  function checkUsernameAvailability() {
    const username = document.getElementById('newUsername').value.trim();
    const msgDiv = document.getElementById('usernameAvailabilityMsg');
    const createBtn = document.getElementById('createBtn');
    if (username.length === 0) {
      msgDiv.innerHTML = '';
      isUsernameAvailable = false;
      isUsernameLengthValid = false;
      createBtn.disabled = true;
      return;
    }
    if (username.length < 8) {
      msgDiv.innerHTML = '<span class="invalid-length">❌ Username must be at least 8 characters</span>';
      isUsernameLengthValid = false;
      isUsernameAvailable = false;
      createBtn.disabled = true;
      return;
    }
    isUsernameLengthValid = true;
    msgDiv.innerHTML = '<span style="color:#6b7280;">⏳ Checking uniqueness...</span>';
    fetch(`/check-username?username=${encodeURIComponent(username)}`)
      .then(r => r.json())
      .then(data => {
        if (data.available) {
          msgDiv.innerHTML = '<span class="username-available">✅ Username available</span>';
          isUsernameAvailable = true;
          updateCreateButtonState();
        } else {
          msgDiv.innerHTML = '<span class="username-taken">❌ Username already taken (global unique)</span>';
          isUsernameAvailable = false;
          createBtn.disabled = true;
        }
      })
      .catch(() => {
        msgDiv.innerHTML = '<span style="color:#dc2626;">⚠️ Network error</span>';
        isUsernameAvailable = false;
        createBtn.disabled = true;
      });
  }

  function onUsernameInput() {
    if (usernameCheckTimeout) clearTimeout(usernameCheckTimeout);
    usernameCheckTimeout = setTimeout(checkUsernameAvailability, 450);
  }

  function updateCreateButtonState() {
    const tipOk = document.getElementById('tipCheck').checked;
    const counterOk = (document.querySelector('input[name="counterOption"]:checked').value === 'existing' && document.getElementById('newExistingCounter').value) ||
                      (document.querySelector('input[name="counterOption"]:checked').value === 'new' && document.getElementById('newCounterName').value.trim() !== "");
    const passwordValid = isPasswordValid(document.getElementById('newPassword').value);
    const matchOk = document.getElementById('newPassword').value === document.getElementById('newConfirm').value;
    const btn = document.getElementById('createBtn');
    if (isUsernameAvailable && isUsernameLengthValid && tipOk && counterOk && passwordValid && matchOk) {
      btn.disabled = false;
    } else {
      btn.disabled = true;
    }
  }

  function isPasswordValid(pwd) { return pwd.length >= 8 && pwd.length <= 18 && /\d/.test(pwd); }

  function checkNewPasswordStrength() {
    const pwd = document.getElementById('newPassword').value;
    const div = document.getElementById('newStrengthMsg');
    if (!pwd) { div.innerHTML = ''; updateCreateButtonState(); return; }
    let lenOk = (pwd.length >= 8 && pwd.length <= 18);
    let hasDigit = /\d/.test(pwd);
    if (lenOk && hasDigit) div.innerHTML = '<span class="strong">✅ Strong password</span>';
    else if (pwd.length < 8) div.innerHTML = '<span class="weak">❌ Too short (min 8)</span>';
    else if (pwd.length > 18) div.innerHTML = '<span class="weak">❌ Exceeds 18</span>';
    else if (!hasDigit) div.innerHTML = '<span class="medium">⚠️ Must contain a number</span>';
    else div.innerHTML = '<span class="medium">⚠️ Weak</span>';
    updateCreateButtonState();
  }

  function checkNewPasswordMatch() {
    const pwd = document.getElementById('newPassword').value;
    const conf = document.getElementById('newConfirm').value;
    const div = document.getElementById('newMatchMsg');
    if (!conf) { div.innerHTML = ''; updateCreateButtonState(); return; }
    if (pwd === conf && pwd !== "") div.innerHTML = '<span class="match-ok">✅ Passwords match</span>';
    else if (pwd !== conf) div.innerHTML = '<span class="match-bad">❌ Passwords do not match</span>';
    updateCreateButtonState();
  }

  function toggleCounterInputs(context) {
    if (context === 'new') {
      const isExisting = document.querySelector('input[name="counterOption"]:checked').value === 'existing';
      document.getElementById('newExistingCounterDiv').style.display = isExisting ? 'block' : 'none';
      document.getElementById('newNewCounterDiv').style.display = isExisting ? 'none' : 'block';
      updateCreateButtonState();
    } else if (context === 'edit') {
      const isExisting = document.querySelector('input[name="editCounterOption"]:checked').value === 'existing';
      document.getElementById('editExistingCounterDiv').style.display = isExisting ? 'block' : 'none';
      document.getElementById('editNewCounterDiv').style.display = isExisting ? 'none' : 'block';
      const renameBlock = document.getElementById('renameCounterBlock');
      if (renameBlock) {
        renameBlock.style.display = isExisting ? 'block' : 'none';
      }
    }
  }

  // Create staff
  function createStaff() {
    const username = document.getElementById('newUsername').value.trim();
    const password = document.getElementById('newPassword').value;
    const confirm = document.getElementById('newConfirm').value;
    const queueId = document.getElementById('queueSelect').value;
    const tipChecked = document.getElementById('tipCheck').checked;

    if (!username || username.length < 8) { toast('Username min 8 chars', 'error'); return; }
    if (!isUsernameAvailable) { toast('Username not available', 'error'); return; }
    if (!isPasswordValid(password)) { toast('Password must be 8-18 chars and contain a digit', 'error'); return; }
    if (password !== confirm) { toast('Passwords do not match', 'error'); return; }
    if (!tipChecked) { toast('Please confirm details', 'error'); return; }

    const counterOption = document.querySelector('input[name="counterOption"]:checked').value;
    let existingCounterId = null, newCounterName = null;
    if (counterOption === 'existing') {
      existingCounterId = document.getElementById('newExistingCounter').value;
      if (!existingCounterId) { toast('Select an existing counter', 'error'); return; }
    } else {
      newCounterName = document.getElementById('newCounterName').value.trim();
      if (!newCounterName) { toast('Enter a name for the new counter', 'error'); return; }
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
    .then(data => {
      if (data.success) { toast(data.success, 'success'); setTimeout(() => location.reload(), 1300); }
      else toast(data.error || 'Creation failed', 'error');
    })
    .catch(() => toast('Network error', 'error'));
  }

  // Load staff details including current queue
  function loadStaffDetails() {
    const select = document.getElementById('staffSelect');
    const opt = select.options[select.selectedIndex];
    if (!select.value) { document.getElementById('editPanel').style.display = 'none'; return; }
    document.getElementById('editUsernameLabel').innerText = opt.getAttribute('data-username');
    document.getElementById('editStatus').value = opt.getAttribute('data-status');
    const counterId = opt.getAttribute('data-counter');
    const currentQueueId = opt.getAttribute('data-queue');
    
    const existingSelect = document.getElementById('editExistingCounter');
    for (let o of existingSelect.options) if (o.value === counterId) { o.selected = true; break; }
    document.getElementById('editCounterName').value = existingSelect.options[existingSelect.selectedIndex]?.getAttribute('data-name') || '';
    
    // Set queue dropdown
    const queueSelect = document.getElementById('editQueueSelect');
    if (currentQueueId) {
      for (let o of queueSelect.options) if (o.value === currentQueueId) { o.selected = true; break; }
    } else {
      queueSelect.value = "";
    }
    
    document.getElementById('editPassword').value = '';
    document.getElementById('editConfirm').value = '';
    document.getElementById('editStrengthMsg').innerHTML = '';
    document.getElementById('editMatchMsg').innerHTML = '';
    document.getElementById('editPanel').setAttribute('data-staff-id', select.value);
    document.getElementById('editPanel').style.display = 'block';
    // reset radio to existing
    document.querySelector('input[name="editCounterOption"][value="existing"]').checked = true;
    toggleCounterInputs('edit');
  }

  function renameCounter() {
    const counterSelect = document.getElementById('editExistingCounter');
    const counterId = counterSelect.value;
    if (!counterId) { toast('No counter selected', 'error'); return; }
    const newName = document.getElementById('editCounterName').value.trim();
    if (!newName) { toast('New counter name required', 'error'); return; }
    fetch(`/update-counter/${counterId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ name: newName })
    })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        toast('Counter renamed');
        const opt = counterSelect.options[counterSelect.selectedIndex];
        opt.setAttribute('data-name', newName);
        opt.textContent = newName;
      } else toast(data.error || 'Rename failed', 'error');
    })
    .catch(() => toast('Network error', 'error'));
  }

  function saveStaffChanges() {
    const staffId = document.getElementById('editPanel').getAttribute('data-staff-id');
    if (!staffId) return;
    const status = document.getElementById('editStatus').value;
    const password = document.getElementById('editPassword').value;
    const confirm = document.getElementById('editConfirm').value;
    const queueId = document.getElementById('editQueueSelect').value;
    
    if (password) {
      if (password !== confirm) { toast('Passwords do not match', 'error'); return; }
      if (!isPasswordValid(password)) { toast('Password 8-18 chars, need a number', 'error'); return; }
    }

    const counterOption = document.querySelector('input[name="editCounterOption"]:checked').value;
    let existingCounterId = null, newCounterName = null;
    if (counterOption === 'existing') {
      existingCounterId = document.getElementById('editExistingCounter').value;
      if (!existingCounterId) { toast('Select an existing counter', 'error'); return; }
    } else {
      newCounterName = document.getElementById('editNewCounterName').value.trim();
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
    .then(data => {
      if (data.success) { toast('Staff updated', 'success'); setTimeout(() => location.reload(), 1000); }
      else toast(data.error || 'Update failed', 'error');
    })
    .catch(() => toast('Network error', 'error'));
  }

  function deleteStaff() {
    const staffId = document.getElementById('editPanel').getAttribute('data-staff-id');
    if (!staffId) return;
    if (!confirm('Permanently delete this staff account?')) return;
    fetch(`/delete-staff/${staffId}`, { method: 'POST' })
      .then(r => r.json())
      .then(data => { if (data.success) { toast('Staff deleted'); setTimeout(() => location.reload(), 1000); } else toast(data.error, 'error'); })
      .catch(() => toast('Network error', 'error'));
  }

  function checkEditPasswordStrength() {
    const pwd = document.getElementById('editPassword').value;
    const div = document.getElementById('editStrengthMsg');
    if (!pwd) { div.innerHTML = ''; return; }
    if (pwd.length>=8 && pwd.length<=18 && /\d/.test(pwd)) div.innerHTML = '<span class="strong">✅ Valid</span>';
    else if (pwd.length<8) div.innerHTML = '<span class="weak">❌ Min 8</span>';
    else if (pwd.length>18) div.innerHTML = '<span class="weak">❌ Max 18</span>';
    else if (!/\d/.test(pwd)) div.innerHTML = '<span class="medium">⚠️ Need a number</span>';
  }
  function checkEditPasswordMatch() {
    const pwd = document.getElementById('editPassword').value;
    const conf = document.getElementById('editConfirm').value;
    const div = document.getElementById('editMatchMsg');
    if (!conf) { div.innerHTML = ''; return; }
    div.innerHTML = (pwd === conf) ? '<span class="match-ok">✅ Match</span>' : '<span class="match-bad">❌ Mismatch</span>';
  }

  window.onload = () => {
    toggleMode();
    document.getElementById('newUsername')?.addEventListener('input', onUsernameInput);
    document.getElementById('tipCheck')?.addEventListener('change', updateCreateButtonState);
    document.getElementById('newExistingCounter')?.addEventListener('change', updateCreateButtonState);
    document.getElementById('newCounterName')?.addEventListener('input', updateCreateButtonState);
    document.querySelectorAll('input[name="counterOption"]').forEach(r => r.addEventListener('change', () => { toggleCounterInputs('new'); updateCreateButtonState(); }));
    document.querySelectorAll('input[name="editCounterOption"]').forEach(r => r.addEventListener('change', () => toggleCounterInputs('edit')));
    updateCreateButtonState();
  };
</script>