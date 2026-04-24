const PLANS = {
  free:       { name: 'Free',       limit: 1  },
  analyst:    { name: 'Analyst',    limit: 5  },
  enterprise: { name: 'Enterprise', limit: Infinity }
};


document.addEventListener('DOMContentLoaded', async () => {
  applySidebarUserInfo();

  
});


//APPLIES THE USER INFO
function applySidebarUserInfo() {
  const user = auth.getUser();
  if (!user) return;

  const planKey = user.plan || 'free';
  const plan = PLANS[planKey] || PLANS.free;

  // Sidebar plan name
  const planNameEl = document.getElementById('sidebarPlanName');
  if (planNameEl) {
    planNameEl.textContent = `${plan.name} Plan`;
  }

  // Avatar / name / email
  const avatarEl = document.querySelector('.user-avatar');
  const nameEl   = document.querySelector('.user-name');
  const emailEl  = document.querySelector('.user-email');

  if (avatarEl) avatarEl.textContent = getInitials(user.name);
  if (nameEl)   nameEl.textContent   = user.name;
  if (emailEl)  emailEl.textContent  = user.email;
}

function updateSidebarLimit(usedCount = 0) {
  const user = auth.getUser();
  const plan = PLANS[user?.plan] || PLANS.free;

  const limit = plan.limit === Infinity ? '∞' : plan.limit;

  const el = document.getElementById('sidebarPlanLimit');
  if (el) {
    el.textContent = `${usedCount} / ${limit} dashboards`;
  }
}

//DROPDOWN FUNCTIONALITY
function toggleUserMenu(e) {
  e.stopPropagation();

  const row = document.getElementById('userRow');
  const dropdown = document.getElementById('userDropdown');

  const isOpen = dropdown.classList.contains('open');
  closeUserMenu();

  if (!isOpen) {
    dropdown.classList.add('open');
    row.classList.add('open');
  }
}

function closeUserMenu() {
  document.getElementById('userDropdown')?.classList.remove('open');
  document.getElementById('userRow')?.classList.remove('open');
}

function handleLogout() {
  auth.clearSession();
  window.location.href = '/';
}

//GLOBAL LISTENERS
document.addEventListener('click', () => closeUserMenu());

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeUserMenu();
});


