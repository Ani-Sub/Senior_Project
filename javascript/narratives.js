// ── MOCK DATA ─────────────────────────────────────────────────
// TODO: Replace with real API calls to GET /api/v1/dashboards/:id/narratives

const MOCK_NARRATIVES = [
  {
    id: 'n1',
    name: 'AGI Timeline Debate',
    color: '#00d4ff',
    direction: 'rising',
    change: +24,
    claims: 312,
    channels: 7,
    factualPct: 28,
    summary: 'Ongoing debate about when artificial general intelligence will be achieved, with creators offering predictions ranging from 2 to 50+ years. Heated disagreement between optimists and skeptics.',
  },
  {
    id: 'n2',
    name: 'LLM Benchmark Disputes',
    color: '#ff6b35',
    direction: 'peaking',
    change: +8,
    claims: 248,
    channels: 5,
    factualPct: 61,
    summary: 'Growing controversy over whether popular benchmarks like MMLU and HumanEval accurately represent real-world model capabilities, with accusations of benchmark overfitting.',
  },
  {
    id: 'n3',
    name: 'Open Source vs Closed',
    color: '#22c55e',
    direction: 'stable',
    change: +2,
    claims: 195,
    channels: 9,
    factualPct: 44,
    summary: 'Debate over whether open-source models will eventually match closed-source frontier models, and whether openness is beneficial or dangerous for AI development.',
  },
  {
    id: 'n4',
    name: 'AI Safety Concerns',
    color: '#f59e0b',
    direction: 'rising',
    change: +31,
    claims: 167,
    channels: 6,
    factualPct: 35,
    summary: 'Increasing discussion about alignment risks, existential threats, and the need for regulatory frameworks to govern advanced AI systems before they become uncontrollable.',
  },
  {
    id: 'n5',
    name: 'Model Cost & Efficiency',
    color: '#a78bfa',
    direction: 'declining',
    change: -14,
    claims: 143,
    channels: 4,
    factualPct: 72,
    summary: 'Claims tracking the dramatic decline in inference and training costs, driven by architectural improvements like MoE, quantization, and hardware advances.',
  },
  {
    id: 'n6',
    name: 'Regulation & Policy',
    color: '#f472b6',
    direction: 'peaking',
    change: +5,
    claims: 98,
    channels: 3,
    factualPct: 52,
    summary: 'Coverage of government attempts to regulate AI — from the EU AI Act to US executive orders — and creator opinions on whether regulation helps or hinders innovation.',
  },
];

// ── STATE ─────────────────────────────────────────────────────
let activeFilter = 'all';

// ── INIT ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const dashboards = loadDashboards();

  if (dashboards.length === 0) {
    document.getElementById('emptyState').style.display = 'flex';
    document.getElementById('selectorArea').style.display = 'none';
    return;
  }

  // Populate selector, newest first
  const select = document.getElementById('dashboardSelect');
  dashboards
    .slice()
    .sort((a, b) => b.createdAt - a.createdAt)
    .forEach(d => {
      const opt = document.createElement('option');
      opt.value = d.id;
      opt.textContent = d.name;
      select.appendChild(opt);
    });

  // Auto-select from ?id= URL param or fall back to first
  const params = new URLSearchParams(window.location.search);
  const urlId  = params.get('id');
  const autoId = (urlId && dashboards.find(d => d.id === urlId)) ? urlId : dashboards[0].id;
  select.value = autoId;
  loadDashboard(autoId);
});

// ── DASHBOARD SELECTOR ────────────────────────────────────────
function onDashboardChange() {
  const id = document.getElementById('dashboardSelect').value;
  if (id) loadDashboard(id);
}

// ── LOAD DASHBOARD ────────────────────────────────────────────
function loadDashboard(id) {
  document.getElementById('dashContent').style.display = 'block';
  // TODO: fetch GET /api/v1/dashboards/:id/narratives
  //   then call updateStats(data) and renderGrid(data)
  updateStats();
  applyFilters();
}

// ── STAT CARDS ────────────────────────────────────────────────
function updateStats() {
  document.getElementById('statTotal').textContent    = MOCK_NARRATIVES.length;
  document.getElementById('statRising').textContent   = MOCK_NARRATIVES.filter(n => n.direction === 'rising').length;
  document.getElementById('statPeaking').textContent  = MOCK_NARRATIVES.filter(n => n.direction === 'peaking').length;
  document.getElementById('statDeclining').textContent = MOCK_NARRATIVES.filter(n => n.direction === 'declining').length;
}

// ── FILTER + SEARCH ───────────────────────────────────────────
function setFilter(btn) {
  document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  activeFilter = btn.dataset.filter;
  applyFilters();
}

function applyFilters() {
  const search = document.getElementById('narrSearch').value.toLowerCase().trim();

  const filtered = MOCK_NARRATIVES.filter(n => {
    const matchDir    = activeFilter === 'all' || n.direction === activeFilter;
    const matchSearch = !search || n.name.toLowerCase().includes(search) || n.summary.toLowerCase().includes(search);
    return matchDir && matchSearch;
  });

  renderGrid(filtered);
}

function resetFilters() {
  document.getElementById('narrSearch').value = '';
  activeFilter = 'all';
  document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
  document.querySelector('.pill[data-filter="all"]').classList.add('active');
  applyFilters();
}

// ── RENDER GRID ───────────────────────────────────────────────
function renderGrid(narratives) {
  const grid  = document.getElementById('narrGrid');
  const empty = document.getElementById('narrEmpty');
  const count = document.getElementById('narrCount');

  count.textContent = `${narratives.length} narrative${narratives.length !== 1 ? 's' : ''}`;

  if (narratives.length === 0) {
    grid.innerHTML = '';
    empty.style.display = 'flex';
    return;
  }

  empty.style.display = 'none';
  grid.innerHTML = narratives.map(n => narrativeCardHTML(n)).join('');
}

function narrativeCardHTML(n) {
  const sign        = n.change >= 0 ? '+' : '';
  const changeClass = n.change > 0 ? 'up' : n.change < 0 ? 'down' : '';
  const opinionPct  = 100 - n.factualPct;

  return `
    <div class="narr-card" onclick="openNarrative('${n.id}')">
      <div class="narr-card-accent" style="background:${n.color}"></div>
      <div class="narr-card-body">
        <div class="narr-card-top">
          <div class="narr-name">${n.name}</div>
          <span class="narr-dir ${n.direction}">${dirLabel(n.direction)}</span>
        </div>
        <p class="narr-summary">${n.summary}</p>
      </div>
      <div class="narr-card-footer">
        <div class="narr-stats">
          <div class="narr-stat-item">
            <span class="narr-stat-val">${n.claims}</span>
            <span>claims</span>
          </div>
          <span class="narr-stat-dot">·</span>
          <div class="narr-stat-item">
            <span class="narr-stat-val">${n.channels}</span>
            <span>channels</span>
          </div>
          <span class="narr-change ${changeClass}">${sign}${n.change}% WoW</span>
        </div>
        <div class="narr-ratio-wrap">
          <div class="narr-ratio-bar">
            <div class="narr-ratio-factual" style="width:${n.factualPct}%"></div>
            <div class="narr-ratio-opinion" style="width:${opinionPct}%"></div>
          </div>
          <div class="narr-ratio-labels">
            <span class="fact">${n.factualPct}% factual</span>
            <span class="opin">${opinionPct}% opinion</span>
          </div>
        </div>
      </div>
    </div>`;
}

// ── NAVIGATE ──────────────────────────────────────────────────
function openNarrative(id) {
  // TODO: navigate to a detailed narrative view or open a side panel
  // e.g. window.location.href = `narrative.html?id=${id}`;
}

// ── HELPERS ───────────────────────────────────────────────────
function dirLabel(d) {
  return { rising: '↑ Rising', peaking: '◆ Peaking', declining: '↓ Declining', stable: '→ Stable' }[d] || d;
}

function loadDashboards() {
  try {
    return JSON.parse(localStorage.getItem('niq_dashboards')) || [];
  } catch {
    return [];
  }
}

// ── USER DROPDOWN ─────────────────────────────────────────────
function toggleUserMenu(e) {
  e.stopPropagation();
  const row      = document.getElementById('userRow');
  const dropdown = document.getElementById('userDropdown');
  const isOpen   = dropdown.classList.contains('open');
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
  // TODO: clear session/token
  window.location.href = '../index.html';
}

document.addEventListener('click', () => closeUserMenu());
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeUserMenu(); });
