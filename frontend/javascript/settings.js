const PLANS = {
  free:       { name: 'Free',       limit: 1  },
  analyst:    { name: 'Analyst',    limit: 5  },
  enterprise: { name: 'Enterprise', limit: Infinity }
};

// Simulated current user — swap this with real auth data from your backend
const CURRENT_USER = {
  name: 'Animesh Subedi',
  email: 'animesh@example.com',
  initials: 'AS',
  plan: 'analyst'   // 'free' | 'analyst' | 'enterprise'
};

// ── INIT ─────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  const el = document.getElementById("currentPlan");
  console.log("currentPlan element:", el);
  if (el) {
    el.textContent = `Current Plan: ${PLANS[CURRENT_USER.plan].name}`;
  } else {
    console.warn("currentPlan element not found!");
  }
  hydrateUserSidebar();
});


//Getting user info and plan info
document.addEventListener('DOMContentLoaded', () => {
  auth.requireAuth();

  const user = auth.getUser();
  if (!user) return;

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

  currentPlanEl.textContent = planLabels[currentPlan] || currentPlan;
  planSelect.value = currentPlan;

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

    // Update local user
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

    // Validation
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
      passStatus.textContent =  error;
      return;
    }

    passStatus.textContent = 'Password updated successfully!';

    // Clear inputs
    currentPassEl.value = '';
    newPassEl.value = '';
    confirmPassEl.value = '';
  });
});



document.getElementById("updatePlanBtn").addEventListener("click", () => {
  document.getElementById("planStatus").textContent = "Plan updated successfully!";
});

document.getElementById("savePaymentBtn").addEventListener("click", () => {
  document.getElementById("paymentStatus").textContent = "Payment details saved!";
});

document.getElementById("saveSecurityBtn").addEventListener("click", () => {
  document.getElementById("securityStatus").textContent = "Security settings updated!";
});

document.getElementById("saveNotifBtn").addEventListener("click", () => {
  document.getElementById("notifStatus").textContent = "Notification preferences saved!";
});




