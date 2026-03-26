// ── MOCK DATA ─────────────────────────────────────────────────
// TODO: Replace with GET /api/v1/claims?dashboard_id=&narrative_id=&type=&risk=&channel=&page=&limit=

const MOCK_NARRATIVES = [
  { id: 'n1', name: 'AGI Timeline Debate',     color: '#00d4ff' },
  { id: 'n2', name: 'LLM Benchmark Disputes',  color: '#ff6b35' },
  { id: 'n3', name: 'Open Source vs Closed',   color: '#22c55e' },
  { id: 'n4', name: 'AI Safety Concerns',      color: '#f59e0b' },
  { id: 'n5', name: 'Model Cost & Efficiency', color: '#a78bfa' },
  { id: 'n6', name: 'Regulation & Policy',     color: '#f472b6' },
];

const MOCK_CLAIMS = [
  { id: 'c1',  text: 'GPT-5 will achieve human-level reasoning within 18 months according to insider sources.',                 type: 'opinion', channel: 'AI Explained',       date: '2025-03-01', narrative: 'n1', confidence: 0.72, risk: 'medium' },
  { id: 'c2',  text: 'Llama 3 outperforms GPT-4 on 6 out of 10 standard benchmarks in independent testing.',                   type: 'factual', channel: 'Two Minute Papers',  date: '2025-02-28', narrative: 'n2', confidence: 0.91, risk: 'low' },
  { id: 'c3',  text: 'The cost to train frontier models has dropped 10x year over year since 2022.',                             type: 'factual', channel: 'Andrej Karpathy',    date: '2025-02-27', narrative: 'n5', confidence: 0.88, risk: 'low' },
  { id: 'c4',  text: 'Closed-source labs are deliberately hiding capability breakthroughs from the public.',                    type: 'opinion', channel: 'Yannic Kilcher',     date: '2025-02-26', narrative: 'n3', confidence: 0.45, risk: 'high' },
  { id: 'c5',  text: 'EU AI Act will significantly slow European AI development compared to US competitors.',                    type: 'opinion', channel: 'AI Supremacy',       date: '2025-02-25', narrative: 'n6', confidence: 0.61, risk: 'medium' },
  { id: 'c6',  text: "Anthropic's Constitutional AI technique reduces harmful outputs by over 80% in red-team tests.",          type: 'factual', channel: 'Lex Fridman',        date: '2025-02-24', narrative: 'n4', confidence: 0.83, risk: 'low' },
  { id: 'c7',  text: 'We are already past the point of no return on AGI development and cannot slow it down.',                  type: 'opinion', channel: 'AI Doomer Pod',      date: '2025-02-23', narrative: 'n1', confidence: 0.38, risk: 'high' },
  { id: 'c8',  text: 'Mixture-of-Experts architectures have reduced inference costs by 40% at comparable quality.',             type: 'factual', channel: 'Wes Roth',           date: '2025-02-22', narrative: 'n5', confidence: 0.79, risk: 'low' },
  { id: 'c9',  text: 'Open-weight models have surpassed GPT-4 quality on coding tasks when fine-tuned on domain data.',        type: 'factual', channel: 'Yannic Kilcher',     date: '2025-02-21', narrative: 'n3', confidence: 0.74, risk: 'low' },
  { id: 'c10', text: 'The benchmark leaderboard is dominated by models that were trained on benchmark test sets.',               type: 'opinion', channel: 'AI Explained',       date: '2025-02-20', narrative: 'n2', confidence: 0.66, risk: 'medium' },
  { id: 'c11', text: 'Regulation without international coordination will only push AI development offshore.',                   type: 'opinion', channel: 'AI Supremacy',       date: '2025-02-19', narrative: 'n6', confidence: 0.58, risk: 'medium' },
  { id: 'c12', text: 'RLHF fundamentally cannot solve alignment because human feedback is inconsistent at scale.',               type: 'opinion', channel: 'AI Doomer Pod',      date: '2025-02-18', narrative: 'n4', confidence: 0.51, risk: 'high' },
  { id: 'c13', text: 'Compute scaling laws are plateauing and will no longer yield proportional capability gains after 2025.',  type: 'opinion', channel: 'Two Minute Papers',  date: '2025-02-17', narrative: 'n1', confidence: 0.63, risk: 'medium' },
  { id: 'c14', text: 'Token efficiency has improved 5x in the last year without any architectural changes.',                    type: 'factual', channel: 'Andrej Karpathy',    date: '2025-02-16', narrative: 'n5', confidence: 0.82, risk: 'low' },
  { id: 'c15', text: 'Meta releasing Llama has set back closed-source labs by 18 months competitively.',                        type: 'opinion', channel: 'Lex Fridman',        date: '2025-02-15', narrative: 'n3', confidence: 0.49, risk: 'medium' },
  { id: 'c16', text: 'GPT-4 still outperforms all open models on complex multi-step reasoning tasks as of Q1 2025.',            type: 'factual', channel: 'Wes Roth',           date: '2025-02-14', narrative: 'n2', confidence: 0.78, risk: 'low' },
];

const PAGE_SIZE = 10;

// ── STATE ─────────────────────────────────────────────────────
let currentPage = 1;
let filteredClaims = [...MOCK_CLAIMS];

// ── INIT ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  buildNarrativeFilters();
  buildChannelFilters();
  checkURLParams();
  filterClaims();
});

// ── URL PARAM PRE-SELECTION ───────────────────────────────────
function checkURLParams() {
  const params = new URLSearchParams(window.location.search);
  const narrativeId = params.get('narrative');
  if (narrativeId) {
    // Deactivate all narrative filter options, then activate only the matching one
    setTimeout(() => {
      document.querySelectorAll('[data-narrative]').forEach(el => {
        el.classList.toggle('active', el.dataset.narrative === narrativeId);
      });
    }, 0);
  }
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
    const matchNarrative = activeNarratives.includes(c.narrative);
    const matchChannel   = activeChannels.includes(c.channel);
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
  const dateFormatted = new Date(c.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  return `
    <div class="feed-claim-card">
      <div class="feed-claim-header">
        <span class="claim-type-badge ${c.type}">${c.type}</span>
        <span class="risk-badge ${c.risk}">${c.risk} risk</span>
        <span class="claim-channel" style="flex:1;margin-left:4px">${c.channel}</span>
        <span class="claim-date">${dateFormatted}</span>
      </div>
      <div class="feed-claim-text">${c.text}</div>
      <div class="feed-claim-footer">
        <span class="narrative-tag">${narr?.name || c.narrative}</span>
        <div class="confidence-bar"><div class="confidence-fill" style="width:${conf}%"></div></div>
        <span class="confidence-label">${conf}% confidence</span>
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
