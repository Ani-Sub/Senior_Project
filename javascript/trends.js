// ── MOCK DATA ─────────────────────────────────────────────────
// TODO: Replace with real API calls to GET /api/v1/dashboards/:id/trends?range=...

const MOCK_NARRATIVES = [
  { id: 'n1', name: 'AGI Timeline Debate',     claims: 312, color: '#00d4ff', direction: 'rising',   change: +24 },
  { id: 'n2', name: 'LLM Benchmark Disputes',  claims: 248, color: '#ff6b35', direction: 'peaking',  change: +8  },
  { id: 'n3', name: 'Open Source vs Closed',   claims: 195, color: '#22c55e', direction: 'stable',   change: +2  },
  { id: 'n4', name: 'AI Safety Concerns',      claims: 167, color: '#f59e0b', direction: 'rising',   change: +31 },
  { id: 'n5', name: 'Model Cost & Efficiency', claims: 143, color: '#a78bfa', direction: 'declining', change: -14 },
  { id: 'n6', name: 'Regulation & Policy',     claims: 98,  color: '#f472b6', direction: 'peaking',  change: +5  },
];

// Hardcoded mock trend data per range to keep chart stable across renders.
// TODO: Replace each range block with the real API response for that ?range= param.
const MOCK_TREND_DATA = {
  '3m': {
    labels: ['Jan W1','Jan W2','Jan W3','Jan W4','Feb W1','Feb W2','Feb W3','Feb W4','Mar W1'],
    datasets: [
      { id: 'n1', label: 'AGI Timeline Debate',    color: '#00d4ff', data: [18,22,28,25,31,38,42,51,58] },
      { id: 'n2', label: 'LLM Benchmark Disputes', color: '#ff6b35', data: [30,35,28,40,45,48,42,50,55] },
      { id: 'n3', label: 'Open Source vs Closed',  color: '#22c55e', data: [22,20,25,23,26,24,28,25,27] },
      { id: 'n4', label: 'AI Safety Concerns',     color: '#f59e0b', data: [12,15,18,14,20,25,22,28,35] },
    ]
  },
  '1m': {
    labels: ['Feb W1','Feb W2','Feb W3','Feb W4'],
    datasets: [
      { id: 'n1', label: 'AGI Timeline Debate',    color: '#00d4ff', data: [31,38,42,51] },
      { id: 'n2', label: 'LLM Benchmark Disputes', color: '#ff6b35', data: [45,48,42,50] },
      { id: 'n3', label: 'Open Source vs Closed',  color: '#22c55e', data: [26,24,28,25] },
      { id: 'n4', label: 'AI Safety Concerns',     color: '#f59e0b', data: [20,25,22,28] },
    ]
  },
  '2w': {
    labels: ['Feb W4','Mar W1'],
    datasets: [
      { id: 'n1', label: 'AGI Timeline Debate',    color: '#00d4ff', data: [51,58] },
      { id: 'n2', label: 'LLM Benchmark Disputes', color: '#ff6b35', data: [50,55] },
      { id: 'n3', label: 'Open Source vs Closed',  color: '#22c55e', data: [25,27] },
      { id: 'n4', label: 'AI Safety Concerns',     color: '#f59e0b', data: [28,35] },
    ]
  },
};

const PERIOD_LABELS = {
  '2w': 'Last 2 weeks',
  '1m': 'Last month',
  '3m': 'Last 3 months',
};

// ── STATE ─────────────────────────────────────────────────────
let currentRange = '3m';
let chartInstance = null;

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

  // Auto-select from ?id= URL param or fall back to first dashboard
  const params = new URLSearchParams(window.location.search);
  const urlId = params.get('id');
  const autoId = (urlId && dashboards.find(d => d.id === urlId)) ? urlId : dashboards[0].id;
  select.value = autoId;
  loadDashboard(autoId);
});

// ── DASHBOARD SELECTOR ────────────────────────────────────────
function onDashboardChange() {
  const id = document.getElementById('dashboardSelect').value;
  if (id) loadDashboard(id);
}

// ── LOAD DASHBOARD DATA ───────────────────────────────────────
function loadDashboard(id) {
  document.getElementById('dashContent').style.display = 'block';

  // TODO: fetch GET /api/v1/dashboards/:id/trends?range=<currentRange>
  //   then call updateStats(data), renderBreakdown(data), renderSummary(data),
  //   and buildChart(data) / updateChart(data) with real response.

  updateStats();
  renderLegend();
  renderBreakdown();
  renderSummary();

  if (!chartInstance) {
    buildChart();
  } else {
    updateChart();
  }
}

// ── STAT CARDS ────────────────────────────────────────────────
function updateStats() {
  const rising   = MOCK_NARRATIVES.filter(n => n.direction === 'rising').length;
  const declining = MOCK_NARRATIVES.filter(n => n.direction === 'declining').length;
  const total    = MOCK_NARRATIVES.reduce((sum, n) => sum + n.claims, 0);

  document.getElementById('statNarratives').textContent = MOCK_NARRATIVES.length;
  document.getElementById('statRising').textContent     = rising;
  document.getElementById('statDeclining').textContent  = declining;
  document.getElementById('statClaims').textContent     = total.toLocaleString();
}

// ── CHART ─────────────────────────────────────────────────────
function buildChart() {
  const ctx = document.getElementById('trendChart').getContext('2d');
  const data = MOCK_TREND_DATA[currentRange];
  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.labels,
      datasets: data.datasets.map(d => datasetConfig(d))
    },
    options: chartOptions()
  });
}

function updateChart() {
  const data = MOCK_TREND_DATA[currentRange];
  chartInstance.data.labels   = data.labels;
  chartInstance.data.datasets = data.datasets.map(d => datasetConfig(d));
  chartInstance.update();
}

function datasetConfig(d) {
  return {
    label: d.label,
    data: d.data,
    borderColor: d.color,
    backgroundColor: d.color + '12',
    borderWidth: 2,
    pointRadius: 3,
    pointHoverRadius: 5,
    tension: 0.4,
    fill: true,
  };
}

// ── RANGE FILTER ──────────────────────────────────────────────
function setRange(btn, range) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentRange = range;
  document.getElementById('periodLabel').textContent = PERIOD_LABELS[range];
  // TODO: re-fetch GET /api/v1/dashboards/:id/trends?range=<range> when API is connected
  if (chartInstance) updateChart();
}

// ── CHART LEGEND ──────────────────────────────────────────────
function renderLegend() {
  const data = MOCK_TREND_DATA['3m'];
  document.getElementById('trendLegend').innerHTML = data.datasets.map(d => `
    <div class="legend-item">
      <div class="legend-dot" style="background:${d.color}"></div>
      <span>${d.label}</span>
    </div>
  `).join('');
}

// ── BREAKDOWN TABLE ───────────────────────────────────────────
function renderBreakdown() {
  const max = Math.max(...MOCK_NARRATIVES.map(n => n.claims));
  document.getElementById('breakdownTable').innerHTML = MOCK_NARRATIVES.map(n => {
    const pct        = (n.claims / max * 100).toFixed(0);
    const sign       = n.change >= 0 ? '+' : '';
    const changeClass = n.change > 0 ? 'up' : n.change < 0 ? 'down' : 'neutral';
    return `
      <div class="breakdown-row">
        <div class="breakdown-dot" style="background:${n.color}"></div>
        <div class="breakdown-name">${n.name}</div>
        <span class="breakdown-dir ${n.direction}">${dirLabel(n.direction)}</span>
        <span class="breakdown-count">${n.claims} claims</span>
        <span class="breakdown-change ${changeClass}">${sign}${n.change}%</span>
        <div class="breakdown-bar-wrap">
          <div class="breakdown-bar" style="width:${pct}%;background:${n.color}"></div>
        </div>
      </div>`;
  }).join('');
}

// ── SUMMARY PANEL ─────────────────────────────────────────────
function renderSummary() {
  const rising   = MOCK_NARRATIVES.filter(n => n.direction === 'rising' || n.direction === 'peaking');
  const declining = MOCK_NARRATIVES.filter(n => n.direction === 'declining');

  document.getElementById('risingList').innerHTML = rising.length
    ? rising.map(n => summaryItemHTML(n, 'rising')).join('')
    : '<p class="summary-empty">No narratives rising this week</p>';

  document.getElementById('decliningList').innerHTML = declining.length
    ? declining.map(n => summaryItemHTML(n, 'declining')).join('')
    : '<p class="summary-empty">No narratives declining this week</p>';
}

function summaryItemHTML(n, type) {
  const icon = type === 'rising' ? '↑' : '↓';
  const abs  = Math.abs(n.change);
  return `
    <div class="summary-item">
      <div class="summary-dot" style="background:${n.color}"></div>
      <div class="summary-info">
        <div class="summary-name">${n.name}</div>
        <div class="summary-stat ${type}">${icon} ${abs}% · ${n.claims} claims</div>
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
        grid:  { color: '#1a253520' },
        ticks: { color: '#4a5a70', font: { family: 'DM Mono', size: 10 } }
      },
      y: {
        beginAtZero: true,
        grid:  { color: '#1a253530' },
        ticks: { color: '#4a5a70', font: { family: 'DM Mono', size: 10 } }
      }
    }
  };
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
