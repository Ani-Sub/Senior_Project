// ── MOCK DATA ─────────────────────────────────────────────────
// TODO: Replace with GET /api/v1/narratives?dashboard_id=&status=&topic=&sort=

const MOCK_NARRATIVES = [
  {
    id: 'n1',
    name: 'AGI Timeline Debate',
    topic: 'AI',
    summary: 'Ongoing discourse about when artificial general intelligence will be achieved, featuring competing predictions from researchers, founders, and skeptics.',
    claims: 312,
    direction: 'rising',
    color: '#00d4ff',
    dateRange: 'Jan 3 – Mar 1, 2025',
    channels: 11,
  },
  {
    id: 'n2',
    name: 'LLM Benchmark Disputes',
    topic: 'AI',
    summary: 'Controversy surrounding the validity and gaming of standard LLM benchmarks, with creators and critics debating methodology and cherry-picked results.',
    claims: 248,
    direction: 'peaking',
    color: '#ff6b35',
    dateRange: 'Jan 10 – Mar 1, 2025',
    channels: 8,
  },
  {
    id: 'n3',
    name: 'Open Source vs Closed',
    topic: 'AI',
    summary: 'Debate between advocates of open-weight model releases and proponents of closed-source development, centered on safety, moats, and community benefit.',
    claims: 195,
    direction: 'stable',
    color: '#22c55e',
    dateRange: 'Dec 14 – Mar 1, 2025',
    channels: 9,
  },
  {
    id: 'n4',
    name: 'AI Safety Concerns',
    topic: 'AI',
    summary: 'Claims and counter-claims about the existential and near-term risks posed by advanced AI systems, from alignment failures to misuse scenarios.',
    claims: 167,
    direction: 'rising',
    color: '#f59e0b',
    dateRange: 'Jan 20 – Mar 1, 2025',
    channels: 7,
  },
  {
    id: 'n5',
    name: 'Model Cost & Efficiency',
    topic: 'AI',
    summary: 'Tracking the rapid decline in LLM inference and training costs, alongside claims about compute efficiency improvements and economic implications.',
    claims: 143,
    direction: 'declining',
    color: '#a78bfa',
    dateRange: 'Feb 1 – Mar 1, 2025',
    channels: 6,
  },
  {
    id: 'n6',
    name: 'Regulation & Policy',
    topic: 'Policy',
    summary: 'Coverage of global AI governance efforts including the EU AI Act, US executive orders, and industry self-regulatory proposals and their projected effects.',
    claims: 98,
    direction: 'peaking',
    color: '#f472b6',
    dateRange: 'Jan 15 – Mar 1, 2025',
    channels: 5,
  },
];

// ── STATE ─────────────────────────────────────────────────────
let activeTopicFilter  = 'all';
let activeStatusFilter = 'all';

// ── INIT ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  applyFilters();
});

// ── FILTER LOGIC ──────────────────────────────────────────────
function applyFilters() {
  const search = (document.getElementById('narrativeSearch')?.value || '').toLowerCase();
  const sort   = document.getElementById('sortSelect')?.value || 'claims';

  let results = MOCK_NARRATIVES.filter(n => {
    const matchTopic  = activeTopicFilter  === 'all' || n.topic === activeTopicFilter;
    const matchStatus = activeStatusFilter === 'all' || n.direction === activeStatusFilter;
    const matchSearch = !search ||
      n.name.toLowerCase().includes(search) ||
      n.summary.toLowerCase().includes(search) ||
      n.topic.toLowerCase().includes(search);
    return matchTopic && matchStatus && matchSearch;
  });

  // Sort
  if (sort === 'claims')  results.sort((a, b) => b.claims - a.claims);
  if (sort === 'recent')  results.sort((a, b) => b.id.localeCompare(a.id));
  if (sort === 'alpha')   results.sort((a, b) => a.name.localeCompare(b.name));

  renderGrid(results);
  document.getElementById('resultsCount').textContent =
    `${results.length} narrative${results.length !== 1 ? 's' : ''}`;
}

// ── CHIP TOGGLE ───────────────────────────────────────────────
function toggleChip(el, group) {
  const groupId = group === 'topic' ? 'topicChips' : 'statusChips';
  document.querySelectorAll(`#${groupId} .chip`).forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  if (group === 'topic')  activeTopicFilter  = el.dataset.val;
  if (group === 'status') activeStatusFilter = el.dataset.val;
  applyFilters();
}

// ── RENDER GRID ───────────────────────────────────────────────
function renderGrid(narratives) {
  const grid       = document.getElementById('narrativesGrid');
  const emptyState = document.getElementById('emptyState');

  if (narratives.length === 0) {
    grid.innerHTML = '';
    emptyState.style.display = 'block';
    return;
  }

  emptyState.style.display = 'none';
  grid.innerHTML = narratives.map(n => narrativeCardHTML(n)).join('');
}

// ── CARD HTML ─────────────────────────────────────────────────
function narrativeCardHTML(n) {
  const dirLabels = {
    rising:   '↑ Rising',
    peaking:  '◆ Peaking',
    declining:'↓ Declining',
    stable:   '→ Stable',
  };

  return `
    <div class="narrative-card" onclick="window.location.href='claims.html?narrative=${n.id}'"
         style="--card-color:${n.color}">
      <style>#nc-${n.id}::before { background: linear-gradient(90deg, ${n.color}, transparent); }</style>
      <div id="nc-${n.id}" class="narrative-card" style="all:unset;position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,${n.color},transparent);opacity:0.7;pointer-events:none;border-radius:12px 12px 0 0;"></div>
      <div class="nc-header">
        <div class="nc-title-row">
          <div class="nc-color-dot" style="background:${n.color}"></div>
          <div class="nc-title">${n.name}</div>
        </div>
        <span class="nc-dir ${n.direction}">${dirLabels[n.direction] || n.direction}</span>
      </div>
      <p class="nc-summary">${n.summary}</p>
      <div class="nc-footer">
        <div class="nc-stat">
          <div class="nc-stat-val">${n.claims}</div>
          <div class="nc-stat-label">Claims</div>
        </div>
        <div class="nc-stat-divider"></div>
        <div class="nc-stat">
          <div class="nc-stat-val">${n.channels}</div>
          <div class="nc-stat-label">Channels</div>
        </div>
        <div class="nc-date-range">${n.dateRange}</div>
        <a class="nc-claims-link" href="claims.html?narrative=${n.id}" onclick="event.stopPropagation()">
          View claims →
        </a>
      </div>
    </div>`;
}

// ── USER DROPDOWN ─────────────────────────────────────────────
function toggleUserMenu(e) {
  e.stopPropagation();
  const row = document.getElementById('userRow');
  const dropdown = document.getElementById('userDropdown');
  const isOpen = dropdown.classList.contains('open');
  closeUserMenu();
  if (!isOpen) { dropdown.classList.add('open'); row.classList.add('open'); }
}

function closeUserMenu() {
  document.getElementById('userDropdown')?.classList.remove('open');
  document.getElementById('userRow')?.classList.remove('open');
}

function handleLogout() { window.location.href = '../index.html'; }

document.addEventListener('click', () => closeUserMenu());
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeUserMenu(); });
