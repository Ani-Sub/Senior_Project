
// ── STATE ────────────────────────────────────────────────────
let dashboards = [];
let tags = [];
let selectedDesign = null;
let pendingDeleteId = null;
let currentStep = 1;

// ── INIT ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  auth.requireAuth();
  await initDashboards();
  applyUserInfo();
  renderDashboards();
  setupTagInput();

  document.getElementById('newDashboardBtn').addEventListener('click', () => {
    const user = auth.getUser();
    const plan = PLANS[user?.plan] || PLANS.free;
    if (dashboards.length >= plan.limit) {
      showLimitBanner();
    } else {
      openNewModal();
    }
  });
});

// ── LOAD DASHBOARDS FROM API ──────────────────────────────────
async function initDashboards() {
  const { data, error } = await api.get('/dashboards');
  if (error) {
    dashboards = [];
    return;
  }
  dashboards = (data || []).map(normalizeDashboard);
}

// Map backend field names to what the UI expects
function normalizeDashboard(d) {
  return {
    id:          d.board_id,
    name:        d.board_name,
    description: d.description,
    tags:        d.search_terms || [],
    design:      d.layout || 'overview',
    createdAt:   new Date(d.created_at).getTime(),
  };
}

// ── USER INFO ─────────────────────────────────────────────────
function applyUserInfo() {
  const user = auth.getUser();
  if (!user) return;

  const planKey = user.plan || 'free';
  const plan = PLANS[planKey] || PLANS.free;
  const used = dashboards.length;
  const limit = plan.limit === Infinity ? '∞' : plan.limit;

  document.getElementById('sidebarPlanName').textContent = `${plan.name} Plan`;
  document.getElementById('sidebarPlanLimit').textContent = `${used} / ${limit} dashboards`;

  // Hide upgrade link for enterprise
  if (planKey === 'enterprise') {
    document.getElementById('upgradeLink').style.display = 'none';
  }

  // Greet by first name
  const firstName = (user.name || '').split(' ')[0];
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  document.querySelector('.page-title').textContent = `${greeting}, ${firstName}`;

  // Fill sidebar user info
  const avatarEl = document.querySelector('.user-avatar');
  const nameEl   = document.querySelector('.user-name');
  const emailEl  = document.querySelector('.user-email');
  if (avatarEl) avatarEl.textContent = getInitials(user.name);
  if (nameEl)   nameEl.textContent   = user.name;
  if (emailEl)  emailEl.textContent  = user.email;
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

  updateSidebarLimit(dashboards.length);
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

async function createDashboard() {
  const user = auth.getUser();
  const plan = PLANS[user?.plan] || PLANS.free;
  if (dashboards.length >= plan.limit) {
    closeNewModal();
    showLimitBanner();
    return;
  }

  const name = document.getElementById('dashName').value.trim();
  const desc = document.getElementById('dashDesc').value.trim();

  const btn = document.querySelector('#step3 .btn-primary');
  if (btn) { btn.disabled = true; btn.textContent = 'Creating...'; }

  const timeout = new Promise(resolve =>
    setTimeout(() => resolve({ data: null, error: 'timeout', status: -1 }), 8000)
  );

  const { data, error, status } = await Promise.race([
    api.post('/dashboards', {
      name,
      description: desc,
      search_terms: [...tags],
      layout: selectedDesign || 'overview',
    }),
    timeout,
  ]);

  if (btn) { btn.disabled = false; btn.textContent = '✓ Create Dashboard'; }

  if (error && status === 0) {
    // True network error — server unreachable, nothing was created
    showFormError(error);
    return;
  }

  // Either success, pipeline error, or timeout — board is in DB, close and refresh
  closeNewModal();
  if (!error && data) {
    dashboards.push(normalizeDashboard(data));
  } else {
    // Show toast immediately — don't wait for initDashboards (backend may still be busy)
    const msg = error === 'timeout'
      ? 'Dashboard created — pipeline is still running in the background.'
      : `Dashboard created, but the pipeline reported an error: ${error}`;
    showToast(msg);
    // Try to reload the list but cap the wait at 5s so the UI doesn't hang
    const reloadCap = new Promise(resolve => setTimeout(resolve, 5000));
    await Promise.race([initDashboards(), reloadCap]);
  }
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

async function confirmDelete() {
  const { error } = await api.delete(`/dashboards/${pendingDeleteId}`);
  if (error) {
    closeDeleteModal();
    return;
  }
  dashboards = dashboards.filter(d => d.id !== pendingDeleteId);
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
  const user = auth.getUser();
  const plan = PLANS[user?.plan] || PLANS.free;
  document.getElementById('limitPlanName').textContent = plan.name;
  banner.style.display = 'flex';
}

// ── TOAST ─────────────────────────────────────────────────────
function showToast(message, durationMs = 6000) {
  const el = document.getElementById('toastNotif');
  if (!el) return;
  el.textContent = message;
  el.style.display = 'block';
  clearTimeout(el._hideTimer);
  el._hideTimer = setTimeout(() => { el.style.display = 'none'; }, durationMs);
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

document.addEventListener('click', () => closeUserMenu());
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      overlay.classList.remove('active');
      if (overlay.id === 'deleteModal') pendingDeleteId = null;
    }
  });
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active'));
    pendingDeleteId = null;
  }
});
