// ── PLAN LIMITS ──────────────────────────────────────────────
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
  plan: 'free'   // 'free' | 'analyst' | 'enterprise'
};

// ── STATE ────────────────────────────────────────────────────
let dashboards = loadDashboards();
let tags = [];
let selectedDesign = null;
let pendingDeleteId = null;
let currentStep = 1;

// ── INIT ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  applyUserInfo();
  renderDashboards();
  setupTagInput();

  document.getElementById('newDashboardBtn').addEventListener('click', () => {
    const plan = PLANS[CURRENT_USER.plan];
    if (dashboards.length >= plan.limit) {
      showLimitBanner();
    } else {
      openNewModal();
    }
  });
});

// ── USER INFO ─────────────────────────────────────────────────
function applyUserInfo() {
  const plan = PLANS[CURRENT_USER.plan];
  const used = dashboards.length;
  const limit = plan.limit === Infinity ? '∞' : plan.limit;

  document.getElementById('sidebarPlanName').textContent = `${plan.name} Plan`;
  document.getElementById('sidebarPlanLimit').textContent = `${used} / ${limit} dashboards`;

  // Hide upgrade link for enterprise
  if (CURRENT_USER.plan === 'enterprise') {
    document.getElementById('upgradeLink').style.display = 'none';
  }

  // Greet by first name
  const firstName = CURRENT_USER.name.split(' ')[0];
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  document.querySelector('.page-title').textContent = `${greeting}, ${firstName}`;
}

// ── RENDER DASHBOARDS ─────────────────────────────────────────
function renderDashboards() {
  const grid = document.getElementById('dashboardGrid');
  const empty = document.getElementById('emptyState');
  const count = document.getElementById('dashCount');

  count.textContent = `${dashboards.length} dashboard${dashboards.length !== 1 ? 's' : ''}`;

  if (dashboards.length === 0) {
    grid.innerHTML = '';
    empty.classList.add('visible');
    return;
  }

  empty.classList.remove('visible');

  grid.innerHTML = dashboards
    .slice()
    .sort((a, b) => b.createdAt - a.createdAt)
    .map(d => dashCardHTML(d))
    .join('');

  updateSidebarLimit();
}

function dashCardHTML(d) {
  const date = new Date(d.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  const tagsHTML = d.tags.slice(0, 3).map(t => `<span class="tag-chip">${t}</span>`).join('');
  const extraTags = d.tags.length > 3 ? `<span class="tag-chip">+${d.tags.length - 3}</span>` : '';

  return `
    <div class="dash-card" onclick="openDashboard('${d.id}')">
      <div class="dash-preview ${d.design}">
        ${previewHTML(d.design)}
      </div>
      <div class="dash-card-actions" onclick="event.stopPropagation()">
        <button class="icon-btn delete" onclick="askDelete('${d.id}', '${escHtml(d.name)}')" title="Delete">✕</button>
      </div>
      <div class="dash-card-body">
        <div class="dash-card-name">${escHtml(d.name)}</div>
        <div class="dash-card-meta">Created ${date} · ${capitalize(d.design)} layout</div>
        <div class="dash-card-tags">${tagsHTML}${extraTags}</div>
      </div>
    </div>
  `;
}

function previewHTML(design) {
  if (design === 'overview') return `
    <div class="mini-block tall"></div>
    <div class="mini-col">
      <div class="mini-block"></div>
      <div class="mini-block"></div>
    </div>`;
  if (design === 'trends') return `
    <div style="display:flex;flex-direction:column;gap:6px;width:100%">
      <div class="mini-block full"></div>
      <div class="mini-row">
        <div class="mini-block"></div>
        <div class="mini-block"></div>
        <div class="mini-block"></div>
      </div>
    </div>`;
  if (design === 'claims') return `
    <div class="mini-sidebar"></div>
    <div class="mini-content">
      <div class="mini-block sm"></div>
      <div class="mini-block sm"></div>
      <div class="mini-block sm"></div>
      <div class="mini-block sm"></div>
    </div>`;
  return '';
}

function updateSidebarLimit() {
  const plan = PLANS[CURRENT_USER.plan];
  const used = dashboards.length;
  const limit = plan.limit === Infinity ? '∞' : plan.limit;
  document.getElementById('sidebarPlanLimit').textContent = `${used} / ${limit} dashboards`;
}

// ── NEW DASHBOARD MODAL ───────────────────────────────────────
function openNewModal() {
  resetForm();
  goStep(1);
  document.getElementById('newModal').classList.add('active');
}

function closeNewModal() {
  document.getElementById('newModal').classList.remove('active');
}

function resetForm() {
  document.getElementById('dashName').value = '';
  document.getElementById('dashDesc').value = '';
  document.getElementById('tagInput').value = '';
  tags = [];
  renderTags();
  selectedDesign = null;
  document.querySelectorAll('.design-card').forEach(c => c.classList.remove('selected'));
  currentStep = 1;
}

function goStep(n) {
  // Validate before advancing
  if (n === 2 && currentStep === 1) {
    const name = document.getElementById('dashName').value.trim();
    if (!name) {
      document.getElementById('dashName').focus();
      document.getElementById('dashName').style.borderColor = 'var(--danger)';
      setTimeout(() => document.getElementById('dashName').style.borderColor = '', 1500);
      return;
    }
  }

  if (n === 3 && currentStep === 2) {
    if (!selectedDesign) {
      document.querySelectorAll('.design-card').forEach(c => {
        c.style.borderColor = 'rgba(239,68,68,0.5)';
        setTimeout(() => c.style.borderColor = '', 1500);
      });
      return;
    }
    populateReview();
  }

  currentStep = n;

  // Show/hide steps
  for (let i = 1; i <= 3; i++) {
    document.getElementById(`step${i}`).style.display = i === n ? 'block' : 'none';
    const ind = document.getElementById(`step-ind-${i}`);
    ind.classList.remove('active', 'done');
    if (i === n) ind.classList.add('active');
    else if (i < n) ind.classList.add('done');
  }
}

function selectDesign(el) {
  document.querySelectorAll('.design-card').forEach(c => c.classList.remove('selected'));
  el.classList.add('selected');
  selectedDesign = el.dataset.design;
}

function populateReview() {
  const name = document.getElementById('dashName').value.trim();
  const desc = document.getElementById('dashDesc').value.trim();
  const designLabels = { overview: 'Overview', trends: 'Trends Focus', claims: 'Claims Feed' };

  document.getElementById('reviewName').textContent = name || '—';
  document.getElementById('reviewDesc').textContent = desc || '—';
  document.getElementById('reviewTags').textContent = tags.length ? tags.join(', ') : '—';
  document.getElementById('reviewDesign').textContent = selectedDesign ? designLabels[selectedDesign] : '—';
}

function createDashboard() {
  const plan = PLANS[CURRENT_USER.plan];
  if (dashboards.length >= plan.limit) {
    closeNewModal();
    showLimitBanner();
    return;
  }

  const name = document.getElementById('dashName').value.trim();
  const desc = document.getElementById('dashDesc').value.trim();

  // Dashboards are immutable after creation — no editing allowed.
  // Users must delete and create a new dashboard to change topic or settings.
  // This prevents bypassing the per-plan dashboard limit via edits.
  const dash = {
    id: 'dash_' + Date.now(),
    name,
    description: desc,
    tags: [...tags],
    design: selectedDesign || 'overview',
    createdAt: Date.now(),
  };

  dashboards.push(dash);
  saveDashboards();
  closeNewModal();
  renderDashboards();
}

// ── TAG INPUT ─────────────────────────────────────────────────
function setupTagInput() {
  const input = document.getElementById('tagInput');
  const wrapper = document.getElementById('tagWrapper');

  wrapper.addEventListener('click', () => input.focus());

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addTag(input.value.trim().replace(/,$/, ''));
    }
    if (e.key === 'Backspace' && input.value === '' && tags.length > 0) {
      tags.pop();
      renderTags();
    }
  });

  input.addEventListener('blur', () => {
    if (input.value.trim()) addTag(input.value.trim());
  });
}

function addTag(val) {
  const input = document.getElementById('tagInput');
  if (!val || tags.includes(val) || tags.length >= 10) {
    input.value = '';
    return;
  }
  tags.push(val);
  input.value = '';
  renderTags();
}

function removeTag(val) {
  tags = tags.filter(t => t !== val);
  renderTags();
}

function renderTags() {
  const list = document.getElementById('tagList');
  list.innerHTML = tags.map(t => `
    <div class="tag">
      ${escHtml(t)}
      <button class="tag-remove" onclick="removeTag('${escHtml(t)}')" type="button">✕</button>
    </div>
  `).join('');
}

// ── DELETE ────────────────────────────────────────────────────
function askDelete(id, name) {
  pendingDeleteId = id;
  document.getElementById('deleteModalSub').textContent =
    `"${name}" will be permanently deleted and cannot be recovered.`;
  document.getElementById('deleteModal').classList.add('active');
}

function closeDeleteModal() {
  pendingDeleteId = null;
  document.getElementById('deleteModal').classList.remove('active');
}

function confirmDelete() {
  dashboards = dashboards.filter(d => d.id !== pendingDeleteId);
  saveDashboards();
  closeDeleteModal();
  renderDashboards();
}

// ── OPEN DASHBOARD ────────────────────────────────────────────
function openDashboard(id) {
  window.location.href = `dashboard.html?id=${id}`;
}

// ── LIMIT BANNER ──────────────────────────────────────────────
function showLimitBanner() {
  const banner = document.getElementById('limitBanner');
  const plan = PLANS[CURRENT_USER.plan];
  document.getElementById('limitPlanName').textContent = plan.name;
  banner.style.display = 'flex';
}

// ── PERSISTENCE (localStorage) ───────────────────────────────
function saveDashboards() {
  localStorage.setItem('niq_dashboards', JSON.stringify(dashboards));
}

function loadDashboards() {
  try {
    return JSON.parse(localStorage.getItem('niq_dashboards')) || [];
  } catch {
    return [];
  }
}

// ── HELPERS ───────────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// ── USER DROPDOWN ─────────────────────────────────────────────
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
  authActions.logout();
}

// Close dropdown when clicking anywhere else
document.addEventListener('click', () => closeUserMenu());
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      overlay.classList.remove('active');
      if (overlay.id === 'deleteModal') pendingDeleteId = null;
    }
  });
});

// Close on Escape
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active'));
    pendingDeleteId = null;
  }
});