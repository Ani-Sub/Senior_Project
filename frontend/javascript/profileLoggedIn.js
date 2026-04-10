// ── INIT ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  auth.requireAuth();
  await loadProfile();
  setupSaveButton();
  setupFadeIn();
});

// ── LOAD PROFILE FROM API ─────────────────────────────────────
async function loadProfile() {
  const { data, error } = await api.get('/users/me');

  // Fall back to cached session user if API fails
  const user = error ? auth.getUser() : data;
  if (!user) return;

  // Sidebar
  const avatarEl = document.querySelector('.user-avatar');
  const nameEl   = document.querySelector('.user-name');
  const emailEl  = document.querySelector('.user-email');
  if (avatarEl) avatarEl.textContent = getInitials(user.name);
  if (nameEl)   nameEl.textContent   = user.name;
  if (emailEl)  emailEl.textContent  = user.email;

  // Profile header
  const headerAvatar = document.querySelector('.avatar');
  const displayName  = document.getElementById('displayName2');
  const displayEmail = document.getElementById('displayEmail2');
  if (headerAvatar) headerAvatar.textContent = getInitials(user.name);
  if (displayName)  displayName.textContent  = user.name;
  if (displayEmail) displayEmail.textContent = user.email;

  // Form fields
  const fullNameInput = document.getElementById('fullName');
  const emailInput    = document.getElementById('email');
  if (fullNameInput) fullNameInput.value = user.name  || '';
  if (emailInput)    emailInput.value    = user.email || '';

  // Plan in Usage Overview
  const planEl = document.querySelector('.stat-box .stat-value.accent');
  if (planEl) {
    const planLabels = { free: 'Free', analyst: 'Analyst', enterprise: 'Enterprise' };
    planEl.textContent = planLabels[user.plan] || user.plan || 'Free';
  }
}

// ── SAVE BUTTON ───────────────────────────────────────────────
function setupSaveButton() {
  const saveBtn = document.getElementById('saveBtn');
  if (!saveBtn) return;

  saveBtn.addEventListener('click', async () => {
    const name  = document.getElementById('fullName').value.trim();
    const email = document.getElementById('email').value.trim();

    if (!name || !email) {
      const statusText = document.getElementById('saveStatus');
      if (statusText) statusText.textContent = 'Name and email are required.';
      return;
    }

    saveBtn.disabled    = true;
    saveBtn.textContent = 'Saving...';

    // NOTE FOR BACKEND: phone (input#phone) and location (input#location) fields
    // exist in the UI but are not yet supported by PATCH /api/v1/users/me.
    // UpdateUserBody needs phone: str | None and location: str | None added.
    const { data, error } = await api.patch('/users/me', { name, email });

    saveBtn.disabled    = false;
    saveBtn.textContent = 'Save Changes';

    const statusText = document.getElementById('saveStatus');

    if (error) {
      if (statusText) statusText.textContent = error;
      return;
    }

    // Update DOM with returned values
    const updated = data;
    const headerAvatar = document.querySelector('.avatar');
    const displayName  = document.getElementById('displayName2');
    const displayEmail = document.getElementById('displayEmail2');
    const avatarEl     = document.querySelector('.user-avatar');
    const nameEl       = document.querySelector('.user-name');
    const emailEl      = document.querySelector('.user-email');

    if (headerAvatar) headerAvatar.textContent = getInitials(updated.name);
    if (displayName)  displayName.textContent  = updated.name;
    if (displayEmail) displayEmail.textContent = updated.email;
    if (avatarEl)     avatarEl.textContent     = getInitials(updated.name);
    if (nameEl)       nameEl.textContent       = updated.name;
    if (emailEl)      emailEl.textContent      = updated.email;

    // Keep localStorage session in sync
    const cachedUser = auth.getUser();
    if (cachedUser) {
      auth.saveSession(auth.getToken(), { ...cachedUser, name: updated.name, email: updated.email });
    }

    if (statusText) statusText.textContent = 'Profile updated successfully.';
  });
}


// ── FADE-IN ANIMATION ─────────────────────────────────────────
function setupFadeIn() {
  const faders = document.querySelectorAll('.fade-in');
  if (faders.length === 0) return;
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); });
  }, { threshold: 0.2 });
  faders.forEach(el => observer.observe(el));
}
