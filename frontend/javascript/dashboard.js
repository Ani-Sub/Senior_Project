// ── STATE ─────────────────────────────────────────────────────
let currentLayout = 'overview';
let overviewChartInstance = null;
let trendsChartInstance = null;
let narratives = [];
let claims = [];
let trendData = null; // { labels: [], datasets: [] }
let dashboardId = null;

// ── INIT ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  auth.requireAuth();
  await loadDashboardMeta();
  renderOverview();
  renderTrends();
  renderClaims();
});

// ── LOAD DASHBOARD META FROM API ─────────────────────────────
async function loadDashboardMeta() {
  const params = new URLSearchParams(window.location.search);
  dashboardId = params.get('id') || localStorage.getItem('niq_dashboard_id');
  if (dashboardId) localStorage.setItem('niq_dashboard_id', dashboardId);

  const user = auth.getUser();
  if (user) {
    const avatarEl = document.querySelector('.user-avatar');
    const nameEl   = document.querySelector('.user-name');
    const emailEl  = document.querySelector('.user-email');
    if (avatarEl) avatarEl.textContent = getInitials(user.name);
    if (nameEl)   nameEl.textContent   = user.name;
    if (emailEl)  emailEl.textContent  = user.email;
  }

  let dash = null;

  if (dashboardId) {
    const [dashRes, narrativesRes, claimsRes, trendsRes] = await Promise.all([
      api.get(`/dashboards/${dashboardId}`),
      api.get(`/dashboards/${dashboardId}/narratives`),
      api.get(`/dashboards/${dashboardId}/claims`),
      api.get(`/dashboards/${dashboardId}/trends`),
    ]);

    if (!dashRes.error) dash = dashRes.data;
    if (!narrativesRes.error) narratives = narrativesRes.data || [];
    if (!claimsRes.error) claims = claimsRes.data?.claims || [];
    if (!trendsRes.error && trendsRes.data?.length > 0) trendData = trendsRes.data[0];
  }

  if (!dash) {
    dash = { name: 'Dashboard', layout: 'overview', search_terms: [], created_at: new Date().toISOString() };
  }

  document.getElementById('dashTitle').textContent = dash.name;
  document.getElementById('dashLayout').textContent = layoutLabel(dash.layout);
  document.getElementById('dashUpdated').textContent = 'Created ' + new Date(dash.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  const chips = document.getElementById('searchTermChips');
  chips.innerHTML = (dash.search_terms || []).map(t => `<span class="term-chip">${t}</span>`).join('');

  switchLayout(dash.layout || 'overview');
}

// ── LAYOUT SWITCHING ──────────────────────────────────────────
function switchLayout(layout) {
  currentLayout = layout;

  ['overview', 'trends', 'claims'].forEach(l => {
    document.getElementById(`layout-${l}`).style.display = l === layout ? 'block' : 'none';
    document.querySelector(`.layout-btn[data-layout="${l}"]`).classList.toggle('active', l === layout);
  });

  if (layout === 'overview' && !overviewChartInstance) buildOverviewChart();
  if (layout === 'trends' && !trendsChartInstance) buildTrendsChart();
}

function layoutLabel(l) {
  return { overview: 'Overview Layout', trends: 'Trends Focus', claims: 'Claims Feed' }[l] || l;
}

// ── RENDER OVERVIEW ───────────────────────────────────────────
function renderOverview() {
  const list = document.getElementById('narrativeList');
  if (narratives.length === 0) {
    list.innerHTML = '<div style="color:var(--muted);font-size:0.82rem;padding:12px 0">No narratives yet</div>';
  } else {
    const max = Math.max(...narratives.map(n => n.claim_count || 0), 1);
    list.innerHTML = narratives.map((n, i) => `
      <div class="narrative-item">
        <span class="narrative-rank">#${i + 1}</span>
        <span class="narrative-name">${n.title}</span>
        <div class="narrative-bar-wrap">
          <div class="narrative-bar" style="width:${((n.claim_count || 0) / max * 100).toFixed(0)}%;background:${n.color}"></div>
        </div>
        <span class="narrative-count">${n.claim_count || 0}</span>
      </div>
    `).join('');
  }

  // Stat cards
  const uniqueChannels = new Set(claims.map(c => c.channel_id).filter(Boolean));
  const highRisk = claims.filter(c => c.risk_level === 'high').length;
  document.getElementById('statTotalClaims').textContent    = claims.length.toLocaleString();
  document.getElementById('statNarrativesFound').textContent = narratives.length;
  document.getElementById('statChannelsTracked').textContent = uniqueChannels.size;
  document.getElementById('statHighRiskClaims').textContent  = highRisk;

  const grid = document.getElementById('overviewClaims');
  if (claims.length === 0) {
    grid.innerHTML = '<div style="color:var(--muted);font-size:0.82rem;padding:12px 0">No claims yet</div>';
  } else {
    grid.innerHTML = claims.slice(0, 4).map(c => claimCardHTML(c)).join('');
  }

  const legend = document.getElementById('overviewLegend');
  legend.innerHTML = (trendData?.datasets || []).map(d => `
    <div class="legend-item">
      <div class="legend-dot" style="background:${d.color}"></div>
      <span>${d.label}</span>
    </div>
  `).join('');
}

function buildOverviewChart() {
  const ctx = document.getElementById('overviewChart').getContext('2d');
  const labels = trendData?.labels || [];
  const datasets = (trendData?.datasets || []).map(d => ({
    label: d.label,
    data: d.data,
    borderColor: d.color,
    backgroundColor: d.color + '15',
    borderWidth: 2,
    pointRadius: 3,
    pointHoverRadius: 5,
    tension: 0.4,
    fill: false,
  }));
  overviewChartInstance = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: chartOptions()
  });
}

// ── RENDER TRENDS ─────────────────────────────────────────────
function renderTrends() {
  const directionMap = {};
  (trendData?.datasets || []).forEach(d => {
    if (d.narrative_id) directionMap[d.narrative_id] = d.direction;
  });

  const breakdown = document.getElementById('breakdownList');
  if (narratives.length === 0) {
    breakdown.innerHTML = '<div style="color:var(--muted);font-size:0.82rem;padding:12px 0">No narratives yet</div>';
  } else {
    breakdown.innerHTML = narratives.map(n => {
      const direction = directionMap[n.narrative_id] || 'stable';
      return `
        <div class="breakdown-item">
          <div class="breakdown-dot" style="background:${n.color}"></div>
          <div class="breakdown-info">
            <div class="breakdown-name">${n.title}</div>
            <div class="breakdown-sub">${n.claim_count || 0} claims this period</div>
          </div>
          <span class="breakdown-dir ${direction}">${dirLabel(direction)}</span>
        </div>
      `;
    }).join('');
  }

  const rising = narratives.filter(n => {
    const dir = directionMap[n.narrative_id];
    return dir === 'rising' || dir === 'peaking';
  });
  document.getElementById('risingList').innerHTML = rising.length > 0
    ? rising.map(n => `
        <div class="rising-item">
          <div class="rising-name">${n.title}</div>
          <div class="rising-stat">${n.claim_count || 0} claims</div>
        </div>
      `).join('')
    : '<div style="color:var(--muted);font-size:0.82rem;padding:12px 0">No rising narratives</div>';
}

function buildTrendsChart() {
  const ctx = document.getElementById('trendsChart').getContext('2d');
  const labels = trendData?.labels || [];
  const datasets = (trendData?.datasets || []).map(d => ({
    label: d.label,
    data: d.data,
    borderColor: d.color,
    backgroundColor: d.color + '10',
    borderWidth: 2,
    pointRadius: 3,
    tension: 0.4,
    fill: true,
  }));
  trendsChartInstance = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: chartOptions()
  });
}

function setTrendRange(btn, _range) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  // TODO: re-fetch trend data by range when API supports it
}

function dirLabel(d) {
  return { rising: '↑ Rising', peaking: '◆ Peaking', declining: '↓ Declining', stable: '→ Stable' }[d] || d;
}

// ── RENDER CLAIMS ─────────────────────────────────────────────
function renderClaims() {
  const nFilters = document.getElementById('narrativeFilters');
  nFilters.innerHTML = narratives.map(n => `
    <div class="filter-option active" onclick="toggleFilter(this)" data-narrative="${n.narrative_id}">
      <div class="filter-dot" style="background:${n.color}"></div>
      ${n.title}
    </div>
  `).join('');

  const channels = [...new Set(claims.map(c => c.channel_name).filter(Boolean))];
  document.getElementById('channelFilters').innerHTML = channels.map(ch => `
    <div class="filter-option active" onclick="toggleFilter(this)" data-channel="${ch}">
      ${ch}
    </div>
  `).join('');

  document.getElementById('claimsCount').textContent = `${claims.length} claim${claims.length !== 1 ? 's' : ''}`;
  renderClaimsFeed(claims);
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
  const showLow     = typeChecks[2]?.checked;
  const showMedium  = typeChecks[3]?.checked;
  const showHigh    = typeChecks[4]?.checked;

  const filtered = claims.filter(c => {
    const matchSearch    = !search || c.claim_text.toLowerCase().includes(search) || (c.channel_name || '').toLowerCase().includes(search);
    const matchNarrative = narratives.length === 0 || activeNarratives.includes(c.narrative_id);
    const matchChannel   = channels.length === 0 || activeChannels.includes(c.channel_name);
    const matchType      = (c.claim_type === 'factual' && showFactual) || (c.claim_type === 'opinion' && showOpinion);
    const matchRisk      = (c.risk_level === 'low' && showLow) || (c.risk_level === 'medium' && showMedium) || (c.risk_level === 'high' && showHigh);
    return matchSearch && matchNarrative && matchChannel && matchType && matchRisk;
  });

  renderClaimsFeed(filtered);
  document.getElementById('claimsCount').textContent = `${filtered.length} claim${filtered.length !== 1 ? 's' : ''}`;
}

function renderClaimsFeed(list) {
  const el = document.getElementById('claimsFeedList');
  if (list.length === 0) {
    el.innerHTML = `<div style="text-align:center;padding:60px 20px;color:var(--muted);font-size:0.82rem;">No claims match your filters</div>`;
    return;
  }
  el.innerHTML = list.map(c => feedClaimHTML(c)).join('');
}

// ── HTML HELPERS ──────────────────────────────────────────────
function claimCardHTML(c) {
  const date = c.published_at ? new Date(c.published_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '—';
  return `
    <div class="claim-card">
      <div class="claim-meta">
        <span class="claim-type-badge ${c.claim_type}">${c.claim_type}</span>
        <span class="claim-channel">${c.channel_name || '—'}</span>
        <span class="claim-date">${date}</span>
      </div>
      <div class="claim-text">${c.claim_text}</div>
    </div>`;
}

function feedClaimHTML(c) {
  const conf = Math.round((c.confidence_score || 0) * 100);
  const date = c.published_at ? new Date(c.published_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '—';
  return `
    <div class="feed-claim-card">
      <div class="feed-claim-header">
        <span class="claim-type-badge ${c.claim_type}">${c.claim_type}</span>
        <span class="risk-badge ${c.risk_level}">${c.risk_level} risk</span>
        <span class="claim-channel" style="flex:1;margin-left:4px">${c.channel_name || '—'}</span>
        <span class="claim-date">${date}</span>
      </div>
      <div class="feed-claim-text">${c.claim_text}</div>
      <div class="feed-claim-footer">
        <span class="narrative-tag">${c.narrative_name || '—'}</span>
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
  const data = { narratives, claims, trends: trendData };
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'dashboard-export.json';
  a.click();
  URL.revokeObjectURL(url);
}

async function refreshData() {
  narratives = [];
  claims = [];
  trendData = null;
  overviewChartInstance?.destroy();
  overviewChartInstance = null;
  trendsChartInstance?.destroy();
  trendsChartInstance = null;
  await loadDashboardMeta();
  renderOverview();
  renderTrends();
  renderClaims();
}