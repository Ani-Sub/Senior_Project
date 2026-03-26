// ── MOCK DATA ─────────────────────────────────────────────────
// TODO: Replace with GET /api/v1/dashboards/:id/trends?range=

const MOCK_NARRATIVES = [
  { id: 'n1', name: 'AGI Timeline Debate',     claims: 312, color: '#00d4ff', direction: 'rising',    change: +24 },
  { id: 'n2', name: 'LLM Benchmark Disputes',  claims: 248, color: '#ff6b35', direction: 'peaking',   change: +11 },
  { id: 'n3', name: 'Open Source vs Closed',   claims: 195, color: '#22c55e', direction: 'stable',    change: +2  },
  { id: 'n4', name: 'AI Safety Concerns',      claims: 167, color: '#f59e0b', direction: 'rising',    change: +18 },
  { id: 'n5', name: 'Model Cost & Efficiency', claims: 143, color: '#a78bfa', direction: 'declining', change: -9  },
  { id: 'n6', name: 'Regulation & Policy',     claims: 98,  color: '#f472b6', direction: 'peaking',   change: +7  },
];

// Trend data keyed by range
const TREND_DATA = {
  '1m': {
    labels: ['Feb W1','Feb W2','Feb W3','Feb W4','Mar W1'],
    seed: 42
  },
  '2w': {
    labels: ['Feb W4','Mar W1'],
    seed: 7
  },
  '3m': {
    labels: ['Jan W1','Jan W2','Jan W3','Jan W4','Feb W1','Feb W2','Feb W3','Feb W4','Mar W1','Mar W2','Mar W3','Mar W4'],
    seed: 99
  }
};

let currentRange = '1m';
let chartInstance = null;

// ── INIT ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  renderLegend();
  buildChart();
  renderBreakdownTable();
  renderSummaryPanels();
});

// ── LEGEND ────────────────────────────────────────────────────
function renderLegend() {
  document.getElementById('trendsLegend').innerHTML = MOCK_NARRATIVES.map(n => `
    <div class="legend-item">
      <div class="legend-dot" style="background:${n.color}"></div>
      <span>${n.name}</span>
    </div>
  `).join('');
}

// ── CHART ─────────────────────────────────────────────────────
function buildChart() {
  if (chartInstance) chartInstance.destroy();
  const range = TREND_DATA[currentRange];

  // Seeded pseudo-random for stable data per range
  function seeded(seed, i) {
    return Math.floor(((Math.sin(seed * 9301 + i * 49297 + 233) * 0.5 + 0.5)) * 60) + 10;
  }

  const datasets = MOCK_NARRATIVES.map((n, ni) => ({
    label: n.name,
    data: range.labels.map((_, i) => seeded(range.seed + ni * 17, i)),
    borderColor: n.color,
    backgroundColor: n.color + '12',
    borderWidth: 2,
    pointRadius: 3,
    pointHoverRadius: 5,
    tension: 0.4,
    fill: false,
  }));

  const ctx = document.getElementById('mainTrendsChart').getContext('2d');
  chartInstance = new Chart(ctx, {
    type: 'line',
    data: { labels: range.labels, datasets },
    options: {
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
    }
  });
}

// ── BREAKDOWN TABLE ───────────────────────────────────────────
function renderBreakdownTable() {
  const sorted = [...MOCK_NARRATIVES].sort((a, b) => b.claims - a.claims);
  document.getElementById('breakdownTable').innerHTML = sorted.map(n => {
    const changeClass = n.change > 0 ? 'up' : n.change < 0 ? 'down' : 'flat';
    const changeStr   = n.change > 0 ? `↑ +${n.change}%` : n.change < 0 ? `↓ ${n.change}%` : '→ 0%';
    return `
      <div class="bt-row" onclick="window.location.href='narratives.html'">
        <div class="bt-dot" style="background:${n.color}"></div>
        <div class="bt-name">${n.name}</div>
        <div class="bt-claims">${n.claims} claims</div>
        <div class="bt-change ${changeClass}">${changeStr}</div>
        <div class="bt-dir ${n.direction}">${dirLabel(n.direction)}</div>
      </div>`;
  }).join('');
}

// ── SUMMARY PANELS ────────────────────────────────────────────
function renderSummaryPanels() {
  const rising   = MOCK_NARRATIVES.filter(n => n.direction === 'rising' || n.direction === 'peaking');
  const declining = MOCK_NARRATIVES.filter(n => n.direction === 'declining');

  document.getElementById('risingPanel').innerHTML = rising.length ? rising.map(n => `
    <div class="summary-item">
      <div class="summary-item-name">${n.name}</div>
      <div class="summary-item-stat up">↑ +${n.change}% this week · ${n.claims} claims</div>
    </div>
  `).join('') : '<div class="summary-empty">No rising narratives</div>';

  document.getElementById('decliningPanel').innerHTML = declining.length ? declining.map(n => `
    <div class="summary-item">
      <div class="summary-item-name">${n.name}</div>
      <div class="summary-item-stat down">↓ ${n.change}% this week · ${n.claims} claims</div>
    </div>
  `).join('') : '<div class="summary-empty">No declining narratives</div>';
}

// ── RANGE FILTER ──────────────────────────────────────────────
function setRange(btn, range) {
  document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentRange = range;
  buildChart();
  // TODO: also re-fetch breakdown data for this range from API
}

// ── DASHBOARD SELECTOR ────────────────────────────────────────
function toggleDashDropdown(e) {
  e.stopPropagation();
  const el = document.getElementById('dashSelector');
  el.classList.toggle('open');
}

function selectDash(optionEl, dashId) {
  document.querySelectorAll('.select-option').forEach(o => o.classList.remove('active'));
  optionEl.classList.add('active');
  document.getElementById('dashSelectorLabel').textContent = optionEl.textContent.trim();
  document.getElementById('dashSelector').classList.remove('open');
  // TODO: re-fetch chart data for selected dashboard via GET /api/v1/dashboards/:dashId/trends?range=
}

document.addEventListener('click', () => {
  document.getElementById('dashSelector')?.classList.remove('open');
});

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
document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeUserMenu(); } });

// ── HELPERS ───────────────────────────────────────────────────
function dirLabel(d) {
  return { rising: '↑ Rising', peaking: '◆ Peaking', declining: '↓ Declining', stable: '→ Stable' }[d] || d;
}
