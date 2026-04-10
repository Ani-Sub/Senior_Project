const ITEMS_PER_PAGE = 6;
let currentPage = 1;

let creators = [];
let filteredCreators = [];
// ── INIT ─────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  auth.requireAuth();
  
  const boardId = getDashboardId(); // already exists in your code

  creators = await fetchCreators(boardId);
  filteredCreators = [...creators];

  renderAll();
  setupSearch();
});


// ── MAIN RENDER ──────────────────────────────────────────────
function renderAll() {
  renderCreators();
  renderStats();
  renderChart();
}


// ── FETCH (COMMENTED FOR NOW) ────────────────────────────────
async function fetchCreators(dashboardId) {
  const { data, error } = await creatorActions.getCreators(dashboardId);

  if (error || !data) {
    console.error("Failed to fetch creators:", error);
    return [];
  }

  return data.map(c => ({
    id: c.channel_id,
    name: c.channel_name,
    handle: `@${c.channel_name.replace(/\s+/g, '').toLowerCase()}`,
    subs: "—",

    // existing
    risk: Math.round((c.risk_score || 0) * 10),
    violations: getViolationsFromRisk(c.risk_level),
    totalClaims: c.total_claims,
    flaggedClaims: c.flagged_claims,
    accuracy: c.accuracy_rate
  }));
}


// ── RENDER CREATORS ──────────────────────────────────────────
function renderCreators() {
  const container = document.getElementById("creatorList");

  // 🛑 safety check (prevents blank screen)
  if (!filteredCreators || filteredCreators.length === 0) {
    container.innerHTML = "<p>No creators found</p>";
    return;
  }

  const start = (currentPage - 1) * ITEMS_PER_PAGE;
  const paginated = filteredCreators.slice(start, start + ITEMS_PER_PAGE);

  container.innerHTML = paginated.map(c => creatorCardHTML(c)).join("");

  renderPagination();
}

function creatorCardHTML(c) {
  const level = getRiskLevel(c.risk);
  const initials = getInitials(c.name);

  if (!c.violations.length) {
    return `
      <div class="creator-card" data-name="${c.name.toLowerCase()}">
        <div class="creator-header">

          <div class="avatar">${initials}</div>

          <div class="creator-info">
            <h3>${c.name}</h3>
            <p>${c.handle} • ${c.subs}</p>
          </div>

          <div class="risk-score ${level}">
            ${c.risk}
            <span>Risk</span>
          </div>

        </div>
        <div class="creator-metrics">
          <div class="metric">
            <span>${c.totalClaims ?? 0}</span>
            <label>Claims</label>
          </div>
          <div class="metric">
            <span>${c.flaggedClaims ?? 0}</span>
            <label>Flagged</label>
          </div>
          <div class="metric">
            <span class="${getAccuracyClass(c.accuracy)}">
              ${Math.round((c.accuracy ?? 0) * 100)}%
            </span>
            <label>Accuracy</label>
          </div>
        </div>

        <div class="verified">
          ✔ Verified creator — no violations detected
        </div>
      </div>
    `;
  }

  return `
    <div class="creator-card" data-name="${c.name.toLowerCase()}">
      <div class="creator-header">

        <div class="avatar">${initials}</div>

        <div class="creator-info">
          <h3>${c.name}</h3>
          <p>${c.handle} • ${c.subs}</p>
        </div>

        <div class="risk-score ${level}">
          ${c.risk}
          <span>Risk</span>
        </div>

      </div>
      <div class="creator-metrics">
          <div class="metric">
            <span>${c.totalClaims ?? 0}</span>
            <label>Claims</label>
          </div>
          <div class="metric">
            <span>${c.flaggedClaims ?? 0}</span>
            <label>Flagged</label>
          </div>
          <div class="metric">
            <span class="${getAccuracyClass(c.accuracy)}">
              ${Math.round((c.accuracy ?? 0) * 100)}%
            </span>
            <label>Accuracy</label>
          </div>
        </div>
      <div class="violation-section">
        <div class="violation-title">⚠ Violations Detected</div>
        <div class="flags">
          ${c.violations.map(v => `<span class="flag">${v}</span>`).join("")}
        </div>
      </div>
    </div>
  `;
}


function renderPagination() {
  const container = document.getElementById("pagination");
  if (!container) return; // prevents crash if missing

  const totalPages = Math.ceil(filteredCreators.length / ITEMS_PER_PAGE);

  container.innerHTML = "";

  if (totalPages <= 1) return;

  for (let i = 1; i <= totalPages; i++) {
    const btn = document.createElement("button");
    btn.innerText = i;
    btn.style.color = "#c0c8d1";

    btn.className = "page-btn";

    if (i === currentPage) {
      btn.classList.add("active");
    }

    btn.onclick = () => {
      currentPage = i;
      renderCreators();
    };

    container.appendChild(btn);
  }

  // PREV BUTTON
  const prev = document.createElement("button");
  prev.innerText = "←";
  prev.className = "page-btn";
  prev.disabled = currentPage === 1;

  prev.onclick = () => {
    currentPage--;
    renderCreators();
  };

  container.appendChild(prev);

  // PAGE NUMBERS (your loop here)

  // NEXT BUTTON
  const next = document.createElement("button");
  next.innerText = "→";
  next.className = "page-btn";
  next.disabled = currentPage === totalPages;

  next.onclick = () => {
    currentPage++;
    renderCreators();
  };

  container.appendChild(next);
  
}
renderCreators();
prev.classList.add("nav");
next.classList.add("nav");

// ── STATS ───────────────────────────────────────────────────
function renderStats() {
  const high = creators.filter(c => c.risk >= 70).length;
  const review = creators.filter(c => c.risk >= 40 && c.risk < 70).length;
  const verified = creators.filter(c => c.risk < 20).length;

  //  NEW aggregated metrics
  const totalClaims = creators.reduce((sum, c) => sum + (c.totalClaims || 0), 0);
  const totalFlagged = creators.reduce((sum, c) => sum + (c.flaggedClaims || 0), 0);

  document.getElementById("statHighRisk").textContent = high;
  document.getElementById("statReview").textContent = review;
  document.getElementById("statVerified").textContent = verified;
  document.getElementById("statTotal").textContent = creators.length;

  console.log("Total Claims:", totalClaims);
  console.log("Flagged Claims:", totalFlagged);
}

// ── CHART ───────────────────────────────────────────────────
function renderChart() {
  const ctx = document.getElementById("riskChart");

  const buckets = {
    critical: creators.filter(c => c.risk >= 90).length,
    high: creators.filter(c => c.risk >= 70 && c.risk < 90).length,
    medium: creators.filter(c => c.risk >= 40 && c.risk < 70).length,
    low: creators.filter(c => c.risk >= 20 && c.risk < 40).length,
    safe: creators.filter(c => c.risk < 20).length
  };

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Critical", "High", "Medium", "Low", "Verified"],
      datasets: [{
        data: Object.values(buckets),
        backgroundColor: [
          "#dc2626",
          "#ea580c",
          "#f59e0b",
          "#84cc16",
          "#10b981"
        ]
      }]
    },
    options: {
      plugins: { legend: { display: false } }
    }
  });
}


// ── SEARCH ───────────────────────────────────────────────────
function setupSearch() {
  const search = document.getElementById("creatorSearch");

  search.addEventListener("input", () => {
    const term = search.value.toLowerCase();

    filteredCreators = creators.filter(c =>
      c.name.toLowerCase().includes(term) ||
      c.handle.toLowerCase().includes(term)
    );

    currentPage = 1; // reset to first page
    renderCreators();
  });
}


// ── HELPERS ──────────────────────────────────────────────────
function getRiskLevel(score) {
  if (score >= 90) return "critical";
  if (score >= 70) return "danger";
  if (score >= 40) return "warn";
  return "safe";
}

function getInitials(name = "") {
  return name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
}

function getDashboardId() {
  //const params = new URLSearchParams(window.location.search);
  //return params.get("id");
  return "f47ac10b-58cc-4372-a567-0e02b2c3d479";
}

function getAccuracyClass(acc = 0) {
  if (acc >= 0.8) return "safe";
  if (acc >= 0.5) return "warn";
  return "danger";
}


function getViolationsFromRisk(level) {
  switch (level) {
    case "high":
      return ["misinfo", "harmful"];
    case "medium":
      return ["misleading"];
    case "low":
      return [];
    default:
      return [];
  }
}

// ── SIDEBAR ──────────────────────────────────────────────────
function toggleUserMenu(e) {
  e.stopPropagation();
  const row = document.getElementById('userRow');
  const dropdown = document.getElementById('userDropdown');
  const isOpen = dropdown.classList.contains('open');
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
  window.location.href = 'index.html';
}

document.addEventListener('click', () => closeUserMenu());
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeUserMenu();
});




// Export
function exportCreators() {
  if (!filteredCreators || filteredCreators.length === 0) {
    alert("No data to export");
    return;
  }

  const rows = [
    [
      'Channel ID',
      'Name',
      'Handle',
      'Subscribers',
      'Risk Score',
      'Risk Level',
      'Total Claims',
      'Flagged Claims',
      'Accuracy (%)',
      'Violations'
    ],

    ...filteredCreators.map(c => [
      c.id,
      `"${c.name.replace(/"/g, '""')}"`,
      c.handle,
      c.subs || "—",
      c.risk,
      getRiskLevel(c.risk),
      c.totalClaims ?? 0,
      c.flaggedClaims ?? 0,
      Math.round((c.accuracy ?? 0) * 100),
      `"${(c.violations || []).join('; ')}"`
    ])
  ];

  const csv = rows.map(r => r.join(',')).join('\n');

  const blob = new Blob([csv], { type: 'text/csv' });
  const url  = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = 'creator-risk-report.csv';
  a.click();

  URL.revokeObjectURL(url);
}