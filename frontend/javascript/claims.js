const PAGE_SIZE = 10;

let MOCK_NARRATIVES = [];
let MOCK_CLAIMS = [];

// ── STATE ─────────────────────────────────────────────────────
let currentPage = 1;
let filteredClaims = [];

function getDashboardId() {
  const id = localStorage.getItem('niq_dashboard_id');
  if (!id) { window.location.href = getRoot() + 'index.html'; return null; }
  return id;
}

// ── INIT ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await fetchClaims();
  buildNarrativeFilters();
  buildChannelFilters();
  applyURLParams();
  filterClaims();
});

// ── FETCH FROM API ────────────────────────────────────────────
async function fetchClaims() {
  const dashboardId = getDashboardId();
  const { data, error } = await api.get(`/dashboards/${dashboardId}/claims`);

  if (error || !data) {
    console.error('Failed to load claims:', error);
    return;
  }

  MOCK_CLAIMS = (data.claims || []).map(c => ({
    id:         c.claim_id,
    text:       c.claim_text,
    type:       c.claim_type,
    channel:    c.channel_name,
    date:       c.published_at ? c.published_at.split('T')[0] : '',
    narrative:  c.narrative_id,
    confidence: c.confidence_score,
    risk:       c.risk_level,
  }));

  // Build narratives list from claims
  const narrativeMap = {};
  (data.claims || []).forEach(c => {
    if (c.narrative_id && !narrativeMap[c.narrative_id]) {
      narrativeMap[c.narrative_id] = { id: c.narrative_id, name: c.narrative_name || c.narrative_id, color: '#00d4ff' };
    }
  });
  MOCK_NARRATIVES = Object.values(narrativeMap);

  filteredClaims = [...MOCK_CLAIMS];
}

// ── URL PARAM PRE-SELECTION ───────────────────────────────────
function applyURLParams() {
  const params = new URLSearchParams(window.location.search);
  const narrativeId = params.get('narrative');
  if (!narrativeId) return;
  document.querySelectorAll('[data-narrative]').forEach(el => {
    el.classList.toggle('active', el.dataset.narrative === narrativeId);
  });
}

// ── BUILD FILTER PANELS ───────────────────────────────────────
function buildNarrativeFilters() {
  document.getElementById('narrativeFilters').innerHTML = MOCK_NARRATIVES.map(n => `
    <div class="filter-option active" onclick="toggleFilter(this)" data-narrative="${n.id}">
      <div class="filter-dot" style="background:${n.color}"></div>
      ${n.name}
    </div>
  `).join('');
}

function buildChannelFilters() {
  const channels = [...new Set(MOCK_CLAIMS.map(c => c.channel))].sort();
  document.getElementById('channelFilters').innerHTML = channels.map(ch => `
    <div class="filter-option active" onclick="toggleFilter(this)" data-channel="${ch}">
      ${ch}
    </div>
  `).join('');
}

// ── FILTER LOGIC ──────────────────────────────────────────────
function filterClaims() {
  currentPage = 1;
  const search  = (document.getElementById('claimsSearch')?.value || '').toLowerCase();
  const sort    = document.getElementById('sortSelect')?.value || 'date';

  const activeNarratives = [...document.querySelectorAll('[data-narrative].active')].map(el => el.dataset.narrative);
  const activeChannels   = [...document.querySelectorAll('[data-channel].active')].map(el => el.dataset.channel);

  const typeChecks = [...document.querySelectorAll('.filter-check input')];
  const showFactual = typeChecks[0]?.checked;
  const showOpinion = typeChecks[1]?.checked;
  const showLow     = typeChecks[2]?.checked;
  const showMedium  = typeChecks[3]?.checked;
  const showHigh    = typeChecks[4]?.checked;

  const dateFrom = document.getElementById('dateFrom')?.value;
  const dateTo   = document.getElementById('dateTo')?.value;

  filteredClaims = MOCK_CLAIMS.filter(c => {
    const matchSearch    = !search || c.text.toLowerCase().includes(search) || c.channel.toLowerCase().includes(search);
    const matchNarrative = activeNarratives.length === 0 || activeNarratives.includes(c.narrative);
    const matchChannel   = activeChannels.length === 0 || activeChannels.includes(c.channel);
    const matchType      = (c.type === 'factual' && showFactual) || (c.type === 'opinion' && showOpinion);
    const matchRisk      = (c.risk === 'low' && showLow) || (c.risk === 'medium' && showMedium) || (c.risk === 'high' && showHigh);
    const matchFrom      = !dateFrom || c.date >= dateFrom;
    const matchTo        = !dateTo   || c.date <= dateTo;
    return matchSearch && matchNarrative && matchChannel && matchType && matchRisk && matchFrom && matchTo;
  });

  // Sort
  if (sort === 'confidence') filteredClaims.sort((a, b) => b.confidence - a.confidence);
  else if (sort === 'risk')  filteredClaims.sort((a, b) => riskOrder(b.risk) - riskOrder(a.risk));
  else                        filteredClaims.sort((a, b) => b.date.localeCompare(a.date));

  renderPage();
}

function riskOrder(r) { return { low: 1, medium: 2, high: 3 }[r] || 0; }

// ── RENDER PAGE ───────────────────────────────────────────────
function renderPage() {
  const total     = filteredClaims.length;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const start     = (currentPage - 1) * PAGE_SIZE;
  const pageClaims = filteredClaims.slice(start, start + PAGE_SIZE);

  document.getElementById('claimsCount').textContent =
    `${total} claim${total !== 1 ? 's' : ''}`;
  document.getElementById('paginationInfo').textContent =
    `Page ${currentPage} of ${totalPages}`;

  const list = document.getElementById('claimsFeedList');
  if (pageClaims.length === 0) {
    list.innerHTML = `<div class="feed-empty">No claims match your filters</div>`;
  } else {
    list.innerHTML = pageClaims.map(c => feedClaimHTML(c)).join('');
  }

  renderPagination(totalPages);
}

// ── PAGINATION ────────────────────────────────────────────────
function renderPagination(totalPages) {
  const pag = document.getElementById('pagination');
  if (totalPages <= 1) { pag.innerHTML = ''; return; }

  let html = `<button class="page-btn" onclick="goPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>←</button>`;

  for (let i = 1; i <= totalPages; i++) {
    if (totalPages > 7 && Math.abs(i - currentPage) > 2 && i !== 1 && i !== totalPages) {
      if (i === 2 || i === totalPages - 1) html += `<span style="color:var(--muted);padding:0 4px;font-size:0.8rem">…</span>`;
      continue;
    }
    html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="goPage(${i})">${i}</button>`;
  }

  html += `<button class="page-btn" onclick="goPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>→</button>`;
  pag.innerHTML = html;
}

function goPage(p) {
  const totalPages = Math.ceil(filteredClaims.length / PAGE_SIZE);
  if (p < 1 || p > totalPages) return;
  currentPage = p;
  renderPage();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── TOGGLE FILTER OPTION ──────────────────────────────────────
function toggleFilter(el) {
  el.classList.toggle('active');
  filterClaims();
}

// ── RESET FILTERS ─────────────────────────────────────────────
function resetFilters() {
  document.getElementById('claimsSearch').value = '';
  document.querySelectorAll('.filter-option').forEach(el => el.classList.add('active'));
  document.querySelectorAll('.filter-check input').forEach(el => el.checked = true);
  document.getElementById('dateFrom').value = '';
  document.getElementById('dateTo').value   = '';
  document.getElementById('sortSelect').value = 'date';
  filterClaims();
}

// ── EXPORT ────────────────────────────────────────────────────
function exportClaims() {
  // TODO: hit GET /api/v1/claims/export?format=csv and stream the response
  const rows = [
    ['id', 'text', 'type', 'channel', 'date', 'narrative', 'confidence', 'risk'],
    ...filteredClaims.map(c => [c.id, `"${c.text.replace(/"/g,'""')}"`, c.type, c.channel, c.date,
      MOCK_NARRATIVES.find(n => n.id === c.narrative)?.name || c.narrative,
      c.confidence, c.risk])
  ];
  const csv = rows.map(r => r.join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = 'claims-export.csv'; a.click();
  URL.revokeObjectURL(url);
}

// ── CLAIM CARD HTML ───────────────────────────────────────────
function feedClaimHTML(c) {
  const conf = Math.round(c.confidence * 100);
  const narr = MOCK_NARRATIVES.find(n => n.id === c.narrative);
  const dateFormatted = c.date ? new Date(c.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '—';
  return `
    <div class="feed-claim-card">
      <div class="feed-claim-header">
        <span class="claim-type-badge ${c.type}">${c.type}</span>
        <span class="risk-badge ${c.risk}">${c.risk} risk</span>
        <span class="claim-channel" style="flex:1;margin-left:4px">${escHtml(c.channel || '—')}</span>
        <span class="claim-date">${dateFormatted}</span>
      </div>
      <div class="feed-claim-text">${escHtml(c.text)}</div>
      <div class="feed-claim-footer">
        <span class="narrative-tag">${narr?.name || c.narrative}</span>
        <div class="confidence-bar"><div class="confidence-fill" style="width:${conf}%"></div></div>
        <span class="confidence-label">${conf}% confidence</span>
      </div>
    </div>`;
}

