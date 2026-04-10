// ── MOCK DATA ─────────────────────────────────────────────────
// TODO: Replace with GET /api/v1/narratives?dashboard_id=&status=&topic=&sort=

let ALL_NARRATIVES = [];

// ── STATE ─────────────────────────────────────────────────────
let activeTopicFilter  = 'all';
let activeStatusFilter = 'all';

// ── INIT ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await loadNarratives();
  
  applyFilters();
});

//Get the narratives
async function loadNarratives() {
  const dashboardId = getDashboardId();

  const { data, error } = await narrativeActions.getNarratives(dashboardId);

  if (error || !data) {
    console.error("Failed to load narratives:", error);
    ALL_NARRATIVES = [];
    return;
  }

  //  Map backend → frontend format
  ALL_NARRATIVES = data.map(n => ({
    id: n.narrative_id,
    name: n.title,
    topic: normalizeTopic(n.topic_label),
    summary: n.summary,
    claims: n.claim_count,
    //direction: "stable", //  placeholder (backend can compute later)
    color: n.color || "#00d4ff",
    dateRange: "—",
    //channels: 0 // optional future
  }));
}

//Helper
function normalizeTopic(label = "") {
  if (label.toLowerCase().includes("artificial")) return "AI";
  if (label.toLowerCase().includes("crypto")) return "Crypto";
  if (label.toLowerCase().includes("climate")) return "Climate";
  if (label.toLowerCase().includes("policy")) return "Policy";
  return label;
}



// ── FILTER LOGIC ──────────────────────────────────────────────
function applyFilters() {
  const search = (document.getElementById('narrativeSearch')?.value || '').toLowerCase();
  const sort   = document.getElementById('sortSelect')?.value || 'claims';

  let results = ALL_NARRATIVES.filter(n => {
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
        
        <!--
        <span class="nc-dir ${n.direction}">${dirLabels[n.direction] || n.direction}</span>
        -->

        </div>
      <p class="nc-summary">${n.summary}</p>
      <div class="nc-footer">
        <div class="nc-stat">
          <div class="nc-stat-val">${n.claims}</div>
          <div class="nc-stat-label">Claims</div>
        </div>
        <div class="nc-stat-divider"></div>
        
        <!-- 
        <div class="nc-stat">
          <div class="nc-stat-val">${n.channels}</div>
          <div class="nc-stat-label">Channels</div>
        </div>
        -->
        
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


function getDashboardId() {
  return "f47ac10b-58cc-4372-a567-0e02b2c3d479"; // fallback
}