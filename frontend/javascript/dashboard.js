// ── MOCK DATA ─────────────────────────────────────────────────
// TODO: Replace with real API calls to /api/v1/dashboards/:id

const MOCK_NARRATIVES = [
  { id: 'n1', name: 'AGI Timeline Debate',        claims: 312, color: '#00d4ff', direction: 'rising'   },
  { id: 'n2', name: 'LLM Benchmark Disputes',     claims: 248, color: '#ff6b35', direction: 'peaking'  },
  { id: 'n3', name: 'Open Source vs Closed',      claims: 195, color: '#22c55e', direction: 'stable'   },
  { id: 'n4', name: 'AI Safety Concerns',         claims: 167, color: '#f59e0b', direction: 'rising'   },
  { id: 'n5', name: 'Model Cost & Efficiency',    claims: 143, color: '#a78bfa', direction: 'declining' },
  { id: 'n6', name: 'Regulation & Policy',        claims: 98,  color: '#f472b6', direction: 'peaking'  },
];

const MOCK_CLAIMS = [
  { id: 'c1', text: 'GPT-5 will achieve human-level reasoning within 18 months according to insider sources.', type: 'opinion', channel: 'AI Explained', date: 'Mar 1', narrative: 'AGI Timeline Debate', confidence: 0.72, risk: 'medium' },
  { id: 'c2', text: 'Llama 3 outperforms GPT-4 on 6 out of 10 standard benchmarks in independent testing.', type: 'factual', channel: 'Two Minute Papers', date: 'Feb 28', narrative: 'LLM Benchmark Disputes', confidence: 0.91, risk: 'low' },
  { id: 'c3', text: 'The cost to train frontier models has dropped 10x year over year since 2022.', type: 'factual', channel: 'Andrej Karpathy', date: 'Feb 27', narrative: 'Model Cost & Efficiency', confidence: 0.88, risk: 'low' },
  { id: 'c4', text: 'Closed-source labs are deliberately hiding capability breakthroughs from the public.', type: 'opinion', channel: 'Yannic Kilcher', date: 'Feb 26', narrative: 'Open Source vs Closed', confidence: 0.45, risk: 'high' },
  { id: 'c5', text: 'EU AI Act will significantly slow European AI development compared to US competitors.', type: 'opinion', channel: 'AI Supremacy', date: 'Feb 25', narrative: 'Regulation & Policy', confidence: 0.61, risk: 'medium' },
  { id: 'c6', text: 'Anthropic\'s Constitutional AI technique reduces harmful outputs by over 80% in red-team tests.', type: 'factual', channel: 'Lex Fridman', date: 'Feb 24', narrative: 'AI Safety Concerns', confidence: 0.83, risk: 'low' },
  { id: 'c7', text: 'We are already past the point of no return on AGI development and cannot slow it down.', type: 'opinion', channel: 'AI Doomer Pod', date: 'Feb 23', narrative: 'AGI Timeline Debate', confidence: 0.38, risk: 'high' },
  { id: 'c8', text: 'Mixture-of-Experts architectures have reduced inference costs by 40% at comparable quality.', type: 'factual', channel: 'Wes Roth', date: 'Feb 22', narrative: 'Model Cost & Efficiency', confidence: 0.79, risk: 'low' },
];

const MOCK_WEEKLY_TREND = {
  labels: ['Jan W1','Jan W2','Jan W3','Jan W4','Feb W1','Feb W2','Feb W3','Feb W4','Mar W1'],
  datasets: MOCK_NARRATIVES.slice(0, 4).map(n => ({
    label: n.name,
    color: n.color,
    data: Array.from({length: 9}, () => Math.floor(Math.random() * 60) + 10)
  }))
};

// ── STATE ─────────────────────────────────────────────────────
let currentLayout = 'overview';
let overviewChartInstance = null;
let trendsChartInstance = null;

// ── INIT ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadDashboardMeta();
  renderOverview();
  renderTrends();
  renderClaims();
});

// ── LOAD DASHBOARD META FROM localStorage ────────────────────
function loadDashboardMeta() {
  const params = new URLSearchParams(window.location.search);
  const id = params.get('id');
  let dash = null;

  try {
    const all = JSON.parse(localStorage.getItem('niq_dashboards')) || [];
    dash = all.find(d => d.id === id);
  } catch {}

  // Fallback to mock if no match
  if (!dash) {
    dash = {
      name: 'AI Industry Trends',
      layout: 'overview',
      tags: ['GPT-5', 'OpenAI', 'AGI', 'LLM'],
      updatedAt: Date.now()
    };
  }

  document.getElementById('dashTitle').textContent = dash.name;
  document.getElementById('dashLayout').textContent = layoutLabel(dash.layout);
  // createdAt is immutable — dashboards cannot be edited after creation.
  // To change topic/settings the user must delete and create a new dashboard.
  document.getElementById('dashUpdated').textContent = 'Created ' + new Date(dash.createdAt || dash.updatedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  const chips = document.getElementById('searchTermChips');
  chips.innerHTML = (dash.tags || []).map(t => `<span class="term-chip">${t}</span>`).join('');

  // Set the saved layout as default
  switchLayout(dash.layout || 'overview');
}

// ── LAYOUT SWITCHING ──────────────────────────────────────────
function switchLayout(layout) {
  currentLayout = layout;

  ['overview', 'trends', 'claims'].forEach(l => {
    document.getElementById(`layout-${l}`).style.display = l === layout ? 'block' : 'none';
    document.querySelector(`.layout-btn[data-layout="${l}"]`).classList.toggle('active', l === layout);
  });

  // Init charts on first show
  if (layout === 'overview' && !overviewChartInstance) buildOverviewChart();
  if (layout === 'trends' && !trendsChartInstance) buildTrendsChart();
}

function layoutLabel(l) {
  return { overview: 'Overview Layout', trends: 'Trends Focus', claims: 'Claims Feed' }[l] || l;
}

// ── RENDER OVERVIEW ───────────────────────────────────────────
function renderOverview() {
  // Narrative list
  const list = document.getElementById('narrativeList');
  const max = Math.max(...MOCK_NARRATIVES.map(n => n.claims));
  list.innerHTML = MOCK_NARRATIVES.map((n, i) => `
    <div class="narrative-item">
      <span class="narrative-rank">#${i + 1}</span>
      <span class="narrative-name">${n.name}</span>
      <div class="narrative-bar-wrap">
        <div class="narrative-bar" style="width:${(n.claims/max*100).toFixed(0)}%;background:${n.color}"></div>
      </div>
      <span class="narrative-count">${n.claims}</span>
    </div>
  `).join('');

  // Claims grid (first 4)
  const grid = document.getElementById('overviewClaims');
  grid.innerHTML = MOCK_CLAIMS.slice(0, 4).map(c => claimCardHTML(c)).join('');

  // Chart legend
  const legend = document.getElementById('overviewLegend');
  legend.innerHTML = MOCK_WEEKLY_TREND.datasets.map(d => `
    <div class="legend-item">
      <div class="legend-dot" style="background:${d.color}"></div>
      <span>${d.label}</span>
    </div>
  `).join('');
}

function buildOverviewChart() {
  const ctx = document.getElementById('overviewChart').getContext('2d');
  overviewChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: MOCK_WEEKLY_TREND.labels,
      datasets: MOCK_WEEKLY_TREND.datasets.map(d => ({
        label: d.label,
        data: d.data,
        borderColor: d.color,
        backgroundColor: d.color + '15',
        borderWidth: 2,
        pointRadius: 3,
        pointHoverRadius: 5,
        tension: 0.4,
        fill: false,
      }))
    },
    options: chartOptions()
  });
}

// ── RENDER TRENDS ─────────────────────────────────────────────
function renderTrends() {
  // Breakdown list
  const breakdown = document.getElementById('breakdownList');
  breakdown.innerHTML = MOCK_NARRATIVES.map(n => `
    <div class="breakdown-item">
      <div class="breakdown-dot" style="background:${n.color}"></div>
      <div class="breakdown-info">
        <div class="breakdown-name">${n.name}</div>
        <div class="breakdown-sub">${n.claims} claims this period</div>
      </div>
      <span class="breakdown-dir ${n.direction}">${dirLabel(n.direction)}</span>
    </div>
  `).join('');

  // Rising list
  const rising = MOCK_NARRATIVES.filter(n => n.direction === 'rising' || n.direction === 'peaking');
  document.getElementById('risingList').innerHTML = rising.map(n => `
    <div class="rising-item">
      <div class="rising-name">${n.name}</div>
      <div class="rising-stat">↑ ${Math.floor(Math.random()*30)+10}% vs last week · ${n.claims} claims</div>
    </div>
  `).join('');
}

function buildTrendsChart() {
  const ctx = document.getElementById('trendsChart').getContext('2d');
  trendsChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: MOCK_WEEKLY_TREND.labels,
      datasets: MOCK_WEEKLY_TREND.datasets.map(d => ({
        label: d.label,
        data: d.data,
        borderColor: d.color,
        backgroundColor: d.color + '10',
        borderWidth: 2,
        pointRadius: 3,
        tension: 0.4,
        fill: true,
      }))
    },
    options: chartOptions()
  });
}

function setTrendRange(btn, range) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  // TODO: filter chart data by range when real API is connected
}

function dirLabel(d) {
  return { rising: '↑ Rising', peaking: '◆ Peaking', declining: '↓ Declining', stable: '→ Stable' }[d] || d;
}

// ── RENDER CLAIMS ─────────────────────────────────────────────
function renderClaims() {
  // Narrative filter options
  const nFilters = document.getElementById('narrativeFilters');
  nFilters.innerHTML = MOCK_NARRATIVES.map(n => `
    <div class="filter-option active" onclick="toggleFilter(this)" data-narrative="${n.id}">
      <div class="filter-dot" style="background:${n.color}"></div>
      ${n.name}
    </div>
  `).join('');

  // Channel filters
  const channels = [...new Set(MOCK_CLAIMS.map(c => c.channel))];
  document.getElementById('channelFilters').innerHTML = channels.map(ch => `
    <div class="filter-option active" onclick="toggleFilter(this)" data-channel="${ch}">
      ${ch}
    </div>
  `).join('');

  renderClaimsFeed(MOCK_CLAIMS);
}

function toggleFilter(el) {
  el.classList.toggle('active');
  filterClaims();
}

function filterClaims() {
  const search = document.getElementById('claimsSearch').value.toLowerCase();

  const activeNarratives = [...document.querySelectorAll('[data-narrative].active')].map(el => el.dataset.narrative);
  const activeChannels = [...document.querySelectorAll('[data-channel].active')].map(el => el.dataset.channel);

  const typeChecks = [...document.querySelectorAll('.filter-check input')];
  const showFactual = typeChecks[0]?.checked;
  const showOpinion = typeChecks[1]?.checked;

  const filtered = MOCK_CLAIMS.filter(c => {
    const matchSearch = !search || c.text.toLowerCase().includes(search) || c.channel.toLowerCase().includes(search);
    const matchNarrative = activeNarratives.some(id => MOCK_NARRATIVES.find(n => n.id === id)?.name === c.narrative);
    const matchChannel = activeChannels.includes(c.channel);
    const matchType = (c.type === 'factual' && showFactual) || (c.type === 'opinion' && showOpinion);
    return matchSearch && matchNarrative && matchChannel && matchType;
  });

  renderClaimsFeed(filtered);
  document.getElementById('claimsCount').textContent = `${filtered.length} claim${filtered.length !== 1 ? 's' : ''}`;
}

function renderClaimsFeed(claims) {
  const list = document.getElementById('claimsFeedList');
  if (claims.length === 0) {
    list.innerHTML = `<div style="text-align:center;padding:60px 20px;color:var(--muted);font-size:0.82rem;">No claims match your filters</div>`;
    return;
  }
  list.innerHTML = claims.map(c => feedClaimHTML(c)).join('');
}

// ── HTML HELPERS ──────────────────────────────────────────────
function claimCardHTML(c) {
  return `
    <div class="claim-card">
      <div class="claim-meta">
        <span class="claim-type-badge ${c.type}">${c.type}</span>
        <span class="claim-channel">${c.channel}</span>
        <span class="claim-date">${c.date}</span>
      </div>
      <div class="claim-text">${c.text}</div>
    </div>`;
}

function feedClaimHTML(c) {
  const conf = Math.round(c.confidence * 100);
  return `
    <div class="feed-claim-card">
      <div class="feed-claim-header">
        <span class="claim-type-badge ${c.type}">${c.type}</span>
        <span class="risk-badge ${c.risk}">${c.risk} risk</span>
        <span class="claim-channel" style="flex:1;margin-left:4px">${c.channel}</span>
        <span class="claim-date">${c.date}</span>
      </div>
      <div class="feed-claim-text">${c.text}</div>
      <div class="feed-claim-footer">
        <span class="narrative-tag">${c.narrative}</span>
        <div class="confidence-bar"><div class="confidence-fill" style="width:${conf}%"></div></div>
        <span class="confidence-label">${conf}% confidence</span>
      </div>
    </div>`;
}

// ── CHART OPTIONS ─────────────────────────────────────────────
function chartOptions() {
  return {
    responsive: true,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#0e1520',
        borderColor: '#243040',
        borderWidth: 1,
        titleColor: '#f0f4f8',
        bodyColor: '#d4dde8',
        padding: 10,
      }
    },
    scales: {
      x: {
        grid: { color: '#1a253520' },
        ticks: { color: '#4a5a70', font: { family: 'DM Mono', size: 10 } }
      },
      y: {
        grid: { color: '#1a253530' },
        ticks: { color: '#4a5a70', font: { family: 'DM Mono', size: 10 } }
      }
    }
  };
}

// ── ACTIONS ───────────────────────────────────────────────────
function exportData() {
  const data = { narratives: MOCK_NARRATIVES, claims: MOCK_CLAIMS };
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'dashboard-export.json';
  a.click();
  URL.revokeObjectURL(url);
}

function refreshData() {
  // TODO: Re-fetch from API
  alert('Refresh will trigger a new data fetch from the backend once connected.');
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

function handleLogout() { window.location.href = 'index.html'; }

document.addEventListener('click', () => closeUserMenu());
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeUserMenu(); });