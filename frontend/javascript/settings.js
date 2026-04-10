document.addEventListener('DOMContentLoaded', () => {
  auth.requireAuth();

  const user = auth.getUser();
  if (!user) return;

  applySidebarUserInfo(); //  correct function

  // ── PLAN ELEMENTS ─────────────────────────────
  const currentPlanEl = document.getElementById('currentPlan');
  const planSelect    = document.getElementById('planSelect');
  const updateBtn     = document.getElementById('updatePlanBtn');
  const planStatus    = document.getElementById('planStatus');

  // ── PASSWORD ELEMENTS ─────────────────────────
  const currentPassEl = document.getElementById('currentPassword');
  const newPassEl     = document.getElementById('newPassword');
  const confirmPassEl = document.getElementById('confirmPassword');
  const savePassBtn   = document.getElementById('savePasswordBtn');
  const passStatus    = document.getElementById('passwordStatus');

  // ── PLAN LOGIC ────────────────────────────────
  const planLabels = {
    free: 'Free Plan',
    analyst: 'Analyst - $49/month',
    enterprise: 'Enterprise - $199/month'
  };

  let currentPlan = user.plan;

  //  Set initial UI
  currentPlanEl.textContent = planLabels[currentPlan] || currentPlan;
  planSelect.value = currentPlan;

  //  Update plan
  updateBtn?.addEventListener('click', async () => {
    const newPlan = planSelect.value;

    if (newPlan === currentPlan) {
      planStatus.textContent = 'You are already on this plan.';
      return;
    }

    planStatus.textContent = 'Updating...';
    updateBtn.disabled = true;

    const { error } = await api.patch('/users/me', {
      plan: newPlan
    });

    updateBtn.disabled = false;

    if (error) {
      planStatus.textContent = error;
      return;
    }

    //  Update local storage
    const updatedUser = { ...user, plan: newPlan };
    localStorage.setItem('niq_user', JSON.stringify(updatedUser));

    currentPlan = newPlan;

    currentPlanEl.textContent = planLabels[newPlan];
    planStatus.textContent = 'Plan updated!';
  });

  // ── PASSWORD LOGIC ────────────────────────────
  savePassBtn?.addEventListener('click', async () => {
    const currentPassword = currentPassEl.value;
    const newPassword     = newPassEl.value;
    const confirmPassword = confirmPassEl.value;

    if (!currentPassword || !newPassword || !confirmPassword) {
      passStatus.textContent = 'Please fill in all fields.';
      return;
    }

    if (newPassword.length < 8) {
      passStatus.textContent = 'Password must be at least 8 characters.';
      return;
    }

    if (newPassword !== confirmPassword) {
      passStatus.textContent = 'Passwords do not match.';
      return;
    }

    passStatus.textContent = 'Updating...';
    savePassBtn.disabled = true;

    const { error } = await api.patch('/users/me', {
      current_password: currentPassword,
      new_password: newPassword
    });

    savePassBtn.disabled = false;

    if (error) {
      passStatus.textContent = error;
      return;
    }

    passStatus.textContent = 'Password updated successfully!';

    currentPassEl.value = '';
    newPassEl.value = '';
    confirmPassEl.value = '';
  });
});








