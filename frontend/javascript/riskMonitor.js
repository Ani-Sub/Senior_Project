let allCreators = [];
let chartInstance = null;

function getDashboardId() {
  return localStorage.getItem('niq_dashboard_id') || "f47ac10b-58cc-4372-a567-0e02b2c3d479";
}

// ── INIT ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await fetchCreators();
  buildChart();
  renderStatCards();
  renderCreatorList(allCreators);
  setupSearch();
});

// ── FETCH ─────────────────────────────────────────────────────
async function fetchCreators() {
  const { data, error } = await api.get(`/dashboards/${getDashboardId()}/creators`);
  if (error || !data) {
    console.error('Failed to load creators:', error);
    return;
  }
  allCreators = data;
}

// ── STAT CARDS ────────────────────────────────────────────────
function renderStatCards() {
  const high   = allCreators.filter(c => c.risk_level === 'high').length;
  const medium = allCreators.filter(c => c.risk_level === 'medium').length;
  const low    = allCreators.filter(c => c.risk_level === 'low').length;

  document.getElementById('statHighRisk').textContent      = high;
  document.getElementById('statMediumRisk').textContent    = medium;
  document.getElementById('statLowRisk').textContent       = low;
  document.getElementById('statTotalChannels').textContent = allCreators.length;
}

// ── CHART ─────────────────────────────────────────────────────
function buildChart() {
  const high   = allCreators.filter(c => c.risk_level === 'high').length;
  const medium = allCreators.filter(c => c.risk_level === 'medium').length;
  const low    = allCreators.filter(c => c.risk_level === 'low').length;

  const ctx = document.getElementById('riskChart');
  if (chartInstance) chartInstance.destroy();
  chartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['High', 'Medium', 'Low'],
      datasets: [{
        label: 'Creators',
        data: [high, medium, low],
        backgroundColor: ['#dc2626', '#f59e0b', '#84cc16'],
      }]
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false } },
        y: { grid: { color: '#1a2535' }, ticks: { stepSize: 1 } }
      }
    }
  });
}

// ── CREATOR LIST ──────────────────────────────────────────────
function renderCreatorList(creators) {
  const list = document.getElementById('creatorList');
  if (creators.length === 0) {
    list.innerHTML = '<div style="color:var(--muted);padding:24px;text-align:center">No creators tracked for this dashboard</div>';
    return;
  }
  list.innerHTML = creators.map(c => creatorCardHTML(c)).join('');
}

function creatorCardHTML(c) {
  const initials   = getInitials(c.channel_name);
  const score      = Math.round((c.risk_score || 0) * 100);
  const riskClass  = c.risk_level === 'high' ? 'danger' : c.risk_level === 'medium' ? 'warn' : 'safe';
  const flagged    = c.flagged_claims || 0;
  const total      = c.total_claims || 0;
  const accuracy   = c.accuracy_rate != null ? `${Math.round(c.accuracy_rate * 100)}% accuracy` : '';

  const body = c.risk_level === 'low'
    ? `<div class="verified">✔ Low risk — ${flagged} flagged out of ${total} claims${accuracy ? ' · ' + accuracy : ''}</div>`
    : `<div class="violation-section">
        <div class="violation-title">⚠ ${flagged} flagged claim${flagged !== 1 ? 's' : ''} out of ${total}${accuracy ? ' · ' + accuracy : ''}</div>
       </div>`;

  return `
    <div class="creator-card" data-name="${c.channel_name.toLowerCase()}">
      <div class="creator-header">
        <div class="avatar">${initials}</div>
        <div class="creator-info">
          <h3>${c.channel_name}</h3>
          <p>${c.channel_id}</p>
        </div>
        <div class="risk-score ${riskClass}">
          ${score}
          <span>Risk</span>
        </div>
      </div>
      ${body}
    </div>`;
}

// ── SEARCH ────────────────────────────────────────────────────
function setupSearch() {
  const search = document.getElementById('creatorSearch');
  search.addEventListener('input', () => {
    const term = search.value.toLowerCase();
    const filtered = allCreators.filter(c => c.channel_name.toLowerCase().includes(term));
    renderCreatorList(filtered);
  });
}