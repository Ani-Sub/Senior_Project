// ── STATE ─────────────────────────────────────────────────────
let allNarratives = [];
let activeTopicFilter  = 'all';
let activeStatusFilter = 'all';

function getDashboardId() {
  return localStorage.getItem('niq_dashboard_id') || "f47ac10b-58cc-4372-a567-0e02b2c3d479";
}

// ── INIT ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await fetchNarratives();
  applyFilters();
});

// ── FETCH FROM API ────────────────────────────────────────────
async function fetchNarratives() {
  const dashboardId = getDashboardId();

  const [narrativesRes, trendsRes] = await Promise.all([
    api.get(`/dashboards/${dashboardId}/narratives`),
    api.get(`/dashboards/${dashboardId}/trends`),
  ]);

  if (narrativesRes.error || !narrativesRes.data) {
    console.error('Failed to load narratives:', narrativesRes.error);
    return;
  }

  // Build direction map from trend datasets
  const directionMap = {};
  if (!trendsRes.error && trendsRes.data?.length > 0) {
    (trendsRes.data[0].datasets || []).forEach(d => {
      if (d.narrative_id) directionMap[d.narrative_id] = d.direction;
    });
  }

  allNarratives = (narrativesRes.data || []).map(n => ({
    id:        n.narrative_id,
    name:      n.title,
    topic:     n.topic_label || 'General',
    summary:   n.summary || '',
    claims:    n.claim_count || 0,
    color:     n.color,
    direction: directionMap[n.narrative_id] || 'stable',
    dateRange: formatDateRange(n.first_seen_at, n.last_seen_at),
  }));
}

function formatDateRange(start, end) {
  if (!start) return '';
  const fmt = d => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  return end ? `${fmt(start)} – ${fmt(end)}` : fmt(start);
}

// ── FILTER LOGIC ──────────────────────────────────────────────
function applyFilters() {
  const search = (document.getElementById('narrativeSearch')?.value || '').toLowerCase();
  const sort   = document.getElementById('sortSelect')?.value || 'claims';

  let results = allNarratives.filter(n => {
    const matchTopic  = activeTopicFilter  === 'all' || n.topic === activeTopicFilter;
    const matchStatus = activeStatusFilter === 'all' || n.direction === activeStatusFilter;
    const matchSearch = !search ||
      n.name.toLowerCase().includes(search) ||
      n.summary.toLowerCase().includes(search) ||
      n.topic.toLowerCase().includes(search);
    return matchTopic && matchStatus && matchSearch;
  });

  if (sort === 'claims') results.sort((a, b) => b.claims - a.claims);
  if (sort === 'recent') results.sort((a, b) => b.id.localeCompare(a.id));
  if (sort === 'alpha')  results.sort((a, b) => a.name.localeCompare(b.name));

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
      <div id="nc-${n.id}" class="narrative-card" style="all:unset;position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,${n.color},transparent);opacity:0.7;pointer-events:none;border-radius:12px 12px 0 0;"></div>
      <div class="nc-header">
        <div class="nc-title-row">
          <div class="nc-color-dot" style="background:${n.color}"></div>
          <div class="nc-title">${n.name}</div>
        </div>
        <span class="nc-dir ${n.direction}">${dirLabels[n.direction] || n.direction}</span>
      </div>
      <p class="nc-summary">${n.summary || '—'}</p>
      <div class="nc-footer">
        <div class="nc-stat">
          <div class="nc-stat-val">${n.claims}</div>
          <div class="nc-stat-label">Claims</div>
        </div>
        <div class="nc-date-range">${n.dateRange}</div>
        <a class="nc-claims-link" href="claims.html?narrative=${n.id}" onclick="event.stopPropagation()">
          View claims →
        </a>
      </div>
    </div>`;
}