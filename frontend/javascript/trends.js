let MOCK_NARRATIVES = [];
let currentRange = '1m';
let chartInstance = null;
let trendsLabels = [];
let trendsDatasets = [];

function getDashboardId() {
  return localStorage.getItem('niq_dashboard_id') || "f47ac10b-58cc-4372-a567-0e02b2c3d479";
}

// ── INIT ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await fetchTrends(currentRange);
});

// ── FETCH FROM API ────────────────────────────────────────────
async function fetchTrends(range) {
  const dashboardId = getDashboardId();
  const { data, error } = await api.get(`/dashboards/${dashboardId}/trends?range=${range}`);

  if (error || !data || !data.length) {
    console.error('Failed to load trends:', error);
    renderStatStrip([]);
    return;
  }

  const first    = data[0];
  trendsLabels   = first.labels || [];
  trendsDatasets = first.datasets || [];

  MOCK_NARRATIVES = trendsDatasets.map(d => ({
    id:        d.narrative_id,
    name:      d.label,
    color:     d.color,
    direction: d.direction,
    claims:    d.data.reduce((a, b) => a + b, 0),
    change:    d.data.length >= 2 ? d.data[d.data.length - 1] - d.data[d.data.length - 2] : 0,
  }));

  renderLegend();
  buildChart();
  renderBreakdownTable();
  renderSummaryPanels();
  renderStatStrip(MOCK_NARRATIVES);
}

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

  const datasets = trendsDatasets.map(d => ({
    label: d.label,
    data: d.data,
    borderColor: d.color,
    backgroundColor: d.color + '12',
    borderWidth: 2,
    pointRadius: 3,
    pointHoverRadius: 5,
    tension: 0.4,
    fill: false,
  }));

  const ctx = document.getElementById('mainTrendsChart').getContext('2d');
  chartInstance = new Chart(ctx, {
    type: 'line',
    data: { labels: trendsLabels, datasets },
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
  fetchTrends(range);
}

// ── DASHBOARD SELECTOR ────────────────────────────────────────
function toggleDashDropdown(e) {
  e.stopPropagation();
  const el = document.getElementById('dashSelector');
  el.classList.toggle('open');
}

function selectDash(optionEl, _dashId) {
  document.querySelectorAll('.select-option').forEach(o => o.classList.remove('active'));
  optionEl.classList.add('active');
  document.getElementById('dashSelectorLabel').textContent = optionEl.textContent.trim();
  document.getElementById('dashSelector').classList.remove('open');
  // TODO: re-fetch chart data for selected dashboard via GET /api/v1/dashboards/:dashId/trends?range=
}

document.addEventListener('click', () => {
  document.getElementById('dashSelector')?.classList.remove('open');
});


// ── STAT STRIP ────────────────────────────────────────────────
function renderStatStrip(narrativesData) {
  const active   = narrativesData.length;
  const rising   = narrativesData.filter(n => n.direction === 'rising' || n.direction === 'peaking').length;
  const total    = narrativesData.reduce((sum, n) => sum + n.claims, 0);
  const peaking  = narrativesData.filter(n => n.direction === 'peaking').length;
  const declining = narrativesData.filter(n => n.direction === 'declining').length;

  const el = id => document.getElementById(id);
  if (el('statActive'))    el('statActive').textContent    = active;
  if (el('statRising'))    el('statRising').textContent    = rising;
  if (el('statTotal'))     el('statTotal').textContent     = total.toLocaleString();
  if (el('statPeaking'))   el('statPeaking').textContent   = peaking;
  if (el('statDeclining')) el('statDeclining').textContent = declining;
}

// ── HELPERS ───────────────────────────────────────────────────
function dirLabel(d) {
  return { rising: '↑ Rising', peaking: '◆ Peaking', declining: '↓ Declining', stable: '→ Stable' }[d] || d;
}
